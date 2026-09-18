import logging
from flask import Blueprint, request
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required, get_jwt
from app import extensions
from app.auth import add_user, login_user
from app.models import Users
from app.schemas import LoginSchema, RegisterSchema
from app.errors import success_response, ApiError
from app.audit import audit_log


logger = logging.getLogger(__name__)

bp = Blueprint("auth", __name__, url_prefix="/auth")
limiter = extensions.limiter
jwt = extensions.jwt
revoked_tokens = extensions.revoked_tokens

register_schema = RegisterSchema()
login_schema = LoginSchema()


# register route
@limiter.limit("3/minute")
@bp.route("/register", methods=["POST"])
def registration():
    data = register_schema.load(request.get_json())
    email = data["email"]
    password = data["password"]

    result = add_user(extensions.db_session, email, password)
    if not result["ok"]:
        audit_log("register", outcome="failed", details={"email": email, "reason": result["error"]})
        raise ApiError(
            code="REGISTER_FAILED",
            message=result["error"],
            status_code=400,
        )

    logger.info("user registered: %s", email)
    logger.info("user id: %s", result["user_id"])
    audit_log("register", user_id=result["user_id"], outcome="success", details={"email": email})

    return success_response(
        code="REGISTER_SUCCESS",
        message="User registered successfully.",
        data={"user_id": result["user_id"], "email": email},
        status_code=201,
    )


# login route
@limiter.limit("5/minute")
@bp.route("/login", methods=["POST"])
def loginuser():
    data = login_schema.load(request.get_json())
    email = data["email"]
    password = data["password"]

    result = login_user(extensions.db_session, email, password)
    if not result["ok"]:
        audit_log("login", outcome="failed", details={"email": email, "reason": result["error"]})
        raise ApiError(
            code="LOGIN_FAILED",
            message="Invalid email or password.",
            status_code=401,
        )

    logger.info("user logged in: %s", email)
    logger.info("user id: %s", result["user_id"])

    user_id = result["user_id"]
    access_token = create_access_token(identity=str(user_id))
    refresh_token = create_refresh_token(identity=str(user_id))

    audit_log("login", user_id=user_id, outcome="success", details={"email": email})

    return success_response(
        code="LOGIN_SUCCESS",
        message="User logged in successfully.",
        data={
            "user_id": user_id,
            "email": email,
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
        status_code=200,
    )


# logout
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    return jwt_payload["jti"] in revoked_tokens


@bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    user_id = int(get_jwt_identity())

    jti = get_jwt()["jti"]
    revoked_tokens.add(jti)

    logger.info("user logged out: user_id=%s", user_id)
    audit_log("logout", user_id=user_id, outcome="success")

    return success_response(
        code="LOGOUT_SUCCESS",
        message="User logged out.",
        data={"user_id": user_id},
        status_code=200,
    )


# session status route
@bp.route("/session-status", methods=["GET"])
@jwt_required()
def session_status():
    user_id = int(get_jwt_identity())

    user = extensions.db_session.query(Users).filter_by(user_id=user_id).first()
    if not user:
        audit_log("session_status", user_id=user_id, outcome="success", details={"logged_in": False})
        return success_response(
            code="SESSION_STATUS_SUCCESS",
            message="Session status loaded.",
            data={"logged_in": False},
            status_code=200,
        )

    audit_log("session_status", user_id=user_id, outcome="success", details={"logged_in": True})

    return success_response(
        code="SESSION_STATUS_SUCCESS",
        message="Session status loaded.",
        data={"logged_in": True, "email": user.email},
        status_code=200,
    )


# token refresh
@bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = int(get_jwt_identity())
    new_access_token = create_access_token(identity=str(user_id))

    audit_log("refresh_token", user_id=user_id, outcome="success")

    return success_response(
        code="TOKEN_REFRESH_SUCCESS",
        message="Access token refreshed.",
        data={"access_token": new_access_token},
        status_code=200,
    )