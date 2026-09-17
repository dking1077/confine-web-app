let prefix = "search";

document.addEventListener("DOMContentLoaded", () => {
    /* ========================================
       DOM REFERENCES
    ======================================== */

    const form = document.getElementById("search_form");
    const resultsDiv = document.getElementById("results");
    const searchDiv = document.getElementById("search");
    const workspaceDiv = document.getElementById("workspace_list");
    const addBtn = document.getElementById("add_btn");
    const removeBtn = document.getElementById("remove_btn");
    const modeSelect = document.getElementById("mode_select");
    const processBtn = document.getElementById("process_btn");
    const inputTextarea = document.getElementById("input_textarea");
    const instructionsTextarea = document.getElementById("instructions_textarea");
    const outputTextarea = document.getElementById("output_textarea");
    const favoritesSearchDiv = document.getElementById("favorites_search");

    const tabs = document.querySelectorAll(".tab");
    const panels = document.querySelectorAll(".panel");

    const PAGE_STATE_KEY = "index_page_state_v1";

    /* ========================================
       STORAGE / PAGE STATE
    ======================================== */

    function getSavedState() {
        const raw = sessionStorage.getItem(PAGE_STATE_KEY);
        if (!raw) return null;

        try {
            return JSON.parse(raw);
        } catch (e) {
            console.warn("Failed to parse saved page state:", e);
            return null;
        }
    }

    function savePageState() {
        const activePanel = document.querySelector(".panel.active")?.id || "search";

        sessionStorage.setItem(
            PAGE_STATE_KEY,
            JSON.stringify({
                resultsHTML: resultsDiv?.innerHTML || "",
                searchHTML: searchDiv?.innerHTML || "",
                workspaceHTML: workspaceDiv?.innerHTML || "",
                inputText: inputTextarea?.value || "",
                instructionsText: instructionsTextarea?.value || "",
                outputText: outputTextarea?.value || "",
                activePanel,
            })
        );
    }

    function restorePageState() {
        const state = getSavedState();
        if (!state) return;

        try {
            if (resultsDiv) resultsDiv.innerHTML = state.resultsHTML || "";
            if (searchDiv) searchDiv.innerHTML = state.searchHTML || "";
            if (workspaceDiv) workspaceDiv.innerHTML = state.workspaceHTML || "";
            if (inputTextarea) inputTextarea.value = state.inputText || "";
            if (instructionsTextarea) instructionsTextarea.value = state.instructionsText || "";
            if (outputTextarea) outputTextarea.value = state.outputText || "";

            setActivePanel(state.activePanel || "search");
            rebindRestoredSelectableItems();
            rebindRestoredWorkspaceToggles();
            normalizeWorkspaceToggles();
            animatePanelPopulate(state.activePanel || "search");
        } catch (e) {
            console.warn("Failed to restore page state:", e);
        }
    }

    function clearIndexUI() {
        sessionStorage.removeItem(PAGE_STATE_KEY);

        if (resultsDiv) resultsDiv.innerHTML = "";
        if (searchDiv) searchDiv.textContent = "SEARCH PANEL";
        if (workspaceDiv) workspaceDiv.innerHTML = "";
        if (inputTextarea) inputTextarea.value = "";
        if (instructionsTextarea) instructionsTextarea.value = "";
        if (outputTextarea) outputTextarea.value = "";

        [
            "concepts_list",
            "semantics_list",
            "instructions_list",
            "input_list",
            "output_list",
            "favorites_search",
        ].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = "";
        });

        setActivePanel("search");
    }

    window.clearIndexUI = clearIndexUI;

    /* ========================================
       HELPERS
    ======================================== */

    function getToken() {
        return localStorage.getItem("access_token");
    }

    function setStatus(code, message, details = "") {
        if (!resultsDiv) return;
        resultsDiv.innerHTML = `code: ${code} &nbsp; message: ${message} &nbsp; details: ${details}`;
    }

    function setError(err) {
        if (!resultsDiv) return;
        resultsDiv.innerHTML = `<p style="color:red;">Error: ${String(err)}</p>`;
    }

    function getActivePanelId() {
        return document.querySelector(".panel.active")?.id || null;
    }

    function setActivePanel(panelId) {
        tabs.forEach((tab) => {
            tab.classList.toggle("active", tab.dataset.tab === panelId);
        });

        panels.forEach((panel) => {
            panel.classList.toggle("active", panel.id === panelId);
        });
    }

    function getPanelListEl(panelId) {
        if (!panelId) return null;
        if (panelId === "workspace") return document.getElementById("workspace_list");
        return document.getElementById(`${panelId}_list`);
    }

    function getSourceDivForAdd() {
        const activeId = getActivePanelId();
        if (activeId === "search") return searchDiv;
        if (activeId === "favorites_search" && favoritesSearchDiv) return favoritesSearchDiv;
        return searchDiv;
    }

    function getSelectedIds(container) {
        if (!container) return [];

        return Array.from(container.querySelectorAll(".selectable-item.selected"))
            .map((el) => el.dataset.id)
            .filter(Boolean);
    }

    function clearSelectedItems(container) {
        container?.querySelectorAll(".selectable-item.selected").forEach((el) => {
            el.classList.remove("selected");
        });
    }

    function toggleSelected(el) {
        el.classList.toggle("selected");
        savePageState();
    }

    function createSelectableResult(text, dataset = {}) {
        const div = document.createElement("div");
        div.classList.add("search-result-item", "selectable-item");
        div.textContent = text;

        Object.entries(dataset).forEach(([key, value]) => {
            div.dataset[key] = value;
        });

        div.addEventListener("click", () => toggleSelected(div));
        return div;
    }

    /* ========================================
       FETCH / RESPONSE HANDLING
    ======================================== */

    async function parseJsonOrThrow(response) {
        const text = await response.text();
        const contentType = response.headers.get("content-type") || "";

        if (!contentType.includes("application/json")) {
            const preview = text.slice(0, 220).replace(/\s+/g, " ");
            throw new Error(
                `Expected JSON, got ${contentType || "unknown"} (status ${response.status}). Body: ${preview}`
            );
        }

        let data;
        try {
            data = JSON.parse(text);
        } catch {
            throw new Error(`Invalid JSON (status ${response.status})`);
        }

        if (!response.ok) {
            throw new Error(data?.message || `Request failed with status ${response.status}`);
        }

        return data;
    }

    async function postJson(url, body) {
        const token = getToken();

        const response = await fetch(url, {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/json",
                ...(token && { Authorization: `Bearer ${token}` }),
            },
            body: JSON.stringify(body),
        });

        return parseJsonOrThrow(response);
    }

    /* ========================================
       ANIMATION HELPERS
    ======================================== */

    function applyPopulateAnimation(el, index) {
        if (!el) return;

        el.classList.remove("item-populate");
        el.style.animationDelay = `${index * 45}ms`;

        requestAnimationFrame(() => {
            el.classList.add("item-populate");
        });

        el.addEventListener(
            "animationend",
            () => {
                el.classList.remove("item-populate");
                el.style.animationDelay = "";
            },
            { once: true }
        );
    }

    function getPanelAnimationItems(panelId) {
        if (panelId === "search") {
            return Array.from(searchDiv?.querySelectorAll(".search-result-item") || []);
        }

        if (panelId === "workspace") {
            return Array.from(workspaceDiv?.querySelectorAll(".workspace-item") || []);
        }

        if (panelId === "concepts" || panelId === "semantics") {
            const listEl = document.getElementById(`${panelId}_list`);
            return Array.from(listEl?.querySelectorAll(".search-result-item") || []);
        }

        return [];
    }

    function animatePanelPopulate(panelId) {
        if (!["search", "workspace", "concepts", "semantics"].includes(panelId)) return;

        getPanelAnimationItems(panelId).forEach((el, index) => {
            applyPopulateAnimation(el, index);
        });
    }

    /* ========================================
       WORKSPACE TOGGLE REBIND / NORMALIZE
    ======================================== */

    function normalizeWorkspaceToggles() {
        workspaceDiv?.querySelectorAll(".lyrics-toggle").forEach((toggle) => {
            const wrapper = toggle.closest(".workspace-item");
            const lyricsBox = wrapper?.querySelector(".lyrics-box");
            const isOpen = lyricsBox?.style.display === "block";

            toggle.setAttribute("aria-label", "Toggle lyrics");
            toggle.textContent = isOpen ? "v" : "<";
        });
    }

    function bindLyricsToggle(toggle) {
        toggle.addEventListener("click", (e) => {
            e.stopPropagation();

            const wrapper = toggle.closest(".workspace-item");
            const lyricsBox = wrapper?.querySelector(".lyrics-box");
            if (!lyricsBox) return;

            const isOpen = lyricsBox.style.display === "block";
            lyricsBox.style.display = isOpen ? "none" : "block";
            toggle.classList.toggle("open", !isOpen);
            toggle.textContent = isOpen ? "<" : "v";

            savePageState();
        });
    }

    function rebindRestoredWorkspaceToggles() {
        workspaceDiv?.querySelectorAll(".lyrics-toggle").forEach(bindLyricsToggle);
    }

    function rebindRestoredSelectableItems() {
        document.querySelectorAll(".panel .selectable-item").forEach((div) => {
            div.addEventListener("click", () => {
                div.classList.toggle("selected");
                savePageState();
            });
        });
    }

    /* ========================================
       RENDERERS
    ======================================== */

    function formatFeatures(features) {
        return features?.length ? ` feat. ${features.join(", ")}` : "";
    }

    function renderResults(data, container) {
        if (!container) return;
        container.innerHTML = "";

        if (!Array.isArray(data) || data.length === 0) {
            container.textContent = "No results";
            return;
        }

        data.forEach((item) => {
            const result = createSelectableResult(
                `${item.artist_name} - ${item.track_name}${formatFeatures(item.features)}`,
                {
                    id: item.commontrack_id,
                    artist: item.artist_name,
                    track: item.track_name,
                }
            );

            container.appendChild(result);
        });

        animatePanelPopulate("search");
    }

    function renderGenericPanel(data, container) {
        if (!container) return;
        container.innerHTML = "";

        if (!Array.isArray(data) || data.length === 0) {
            container.textContent = "No data";
            return;
        }

        data.forEach((item) => {
            const div = createSelectableResult(
                `${item.artist_name || ""}${item.artist_name ? " - " : ""}${item.track_name || item.name || "item"}`,
                {
                    id: item.commontrack_id || item.id || "",
                }
            );

            container.appendChild(div);
        });
    }

    function renderAnalyzePanel(groups, container, type) {
        if (!container) return;
        container.innerHTML = "";

        if (!Array.isArray(groups) || groups.length === 0) {
            container.textContent = "No data";
            return;
        }

        groups.forEach((trackGroup) => {
            const list = Array.isArray(trackGroup[type]) ? trackGroup[type] : [];

            list.forEach((item) => {
                const title =
                    type === "concepts"
                        ? item.display_concept || item.name || "concept"
                        : item.display_semantic || item.name || "semantic";

                const evidence = item.evidence ? `\n"${item.evidence}"` : "";

                const div = createSelectableResult(`${title}${evidence}`, {
                    id: String(item.id || ""),
                    commontrackId: String(trackGroup.commontrack_id || ""),
                    track: trackGroup.track || "",
                    kind: type,
                });

                container.appendChild(div);
            });
        });
    }

    function renderWorkspace(data, container) {
        if (!container) return;
        container.innerHTML = "";

        if (!Array.isArray(data) || data.length === 0) {
            container.textContent = "No workspace data returned";
            return;
        }

        data.forEach((item) => {
            const wrapper = document.createElement("div");
            wrapper.classList.add("workspace-item");
            wrapper.dataset.id = item.commontrack_id;
            wrapper.dataset.artist = item.artist_name;
            wrapper.dataset.track = item.track_name;

            const header = document.createElement("div");
            header.classList.add("workspace-header");

            const title = document.createElement("div");
            title.classList.add("workspace-title", "selectable-item");
            title.textContent = `${item.artist_name} - ${item.track_name}`;
            title.dataset.id = item.commontrack_id;
            title.dataset.artist = item.artist_name;
            title.dataset.track = item.track_name;
            title.addEventListener("click", () => toggleSelected(title));

            const toggle = document.createElement("button");
            toggle.type = "button";
            toggle.classList.add("lyrics-toggle");
            toggle.setAttribute("aria-label", "Toggle lyrics");
            toggle.textContent = "<";

            const lyricsBox = document.createElement("div");
            lyricsBox.classList.add("lyrics-box");
            lyricsBox.style.display = "none";
            lyricsBox.textContent = item.lyrics || "No lyrics available";

            bindLyricsToggle(toggle);

            header.appendChild(title);
            header.appendChild(toggle);
            wrapper.appendChild(header);
            wrapper.appendChild(lyricsBox);

            container.appendChild(wrapper);
        });

        animatePanelPopulate("workspace");
    }

    /* ========================================
       PANEL ACTIONS
    ======================================== */

    async function addSelectedToPanel(targetPanel, sourceContainer = searchDiv) {
        const track_ids = getSelectedIds(sourceContainer);

        if (track_ids.length === 0) {
            setStatus("ADD_TO_PANEL_ERROR", "no tracks selected");
            savePageState();
            return;
        }

        try {
            const data = await postJson("/tabs/add_to_panel", {
                panel: targetPanel,
                items: track_ids,
            });

            setStatus(data.code, data.message, "items added");

            if (Array.isArray(data.data?.result)) {
                renderWorkspace(data.data.result, workspaceDiv);
            } else if (workspaceDiv) {
                workspaceDiv.textContent = "No workspace data returned";
            }

            clearSelectedItems(sourceContainer);
            savePageState();
        } catch (err) {
            console.error(err);
            setError(err);
            savePageState();
        }
    }

    async function removeSelectedFromPanel(targetPanel, sourceContainer) {
        const item_ids = getSelectedIds(sourceContainer);

        if (item_ids.length === 0) {
            setStatus("REMOVE_FROM_PANEL_ERROR", "no items selected");
            savePageState();
            return;
        }

        try {
            const data = await postJson("/tabs/remove_from_panel", {
                panel: targetPanel,
                items: item_ids,
            });

            setStatus(data.code, data.message, "items removed");

            const targetContainer = getPanelListEl(targetPanel);
            if (targetContainer) {
                if (targetPanel === "workspace") {
                    renderWorkspace(data.data?.result, targetContainer);
                } else if (targetPanel === "concepts") {
                    renderAnalyzePanel(data.data?.result, targetContainer, "concepts");
                } else if (targetPanel === "semantics") {
                    renderAnalyzePanel(data.data?.result, targetContainer, "semantics");
                } else {
                    renderGenericPanel(data.data?.result, targetContainer);
                }
            }

            clearSelectedItems(sourceContainer);
            savePageState();
        } catch (err) {
            console.error(err);
            setError(err);
            savePageState();
        }
    }

    async function processSelectedItems() {
        const track_ids = getSelectedIds(workspaceDiv);
        const concept_ids = getSelectedIds(document.getElementById("concepts_list"));
        const semantic_ids = getSelectedIds(document.getElementById("semantics_list"));

        if (track_ids.length === 0) {
            setStatus("PROCESS_ITEMS_ERROR", "no tracks selected in workspace");
            savePageState();
            return;
        }

        const instructions = instructionsTextarea?.value || "";
        const input_text = inputTextarea?.value || "";
        const mode = (modeSelect?.value || "Transform").toLowerCase();
        const route = mode === "analyze" ? "/tabs/analyze_items" : "/tabs/process_items";

        try {
            const data = await postJson(route, {
                items: track_ids,
                concept_ids,
                semantic_ids,
                instructions,
                input_text,
            });

            setStatus(
                data.code,
                data.message,
                "request completed"
            );

            if (route === "/tabs/analyze_items" && data.data?.result) {
                renderAnalyzePanel(data.data.result.concepts, document.getElementById("concepts_list"), "concepts");
                renderAnalyzePanel(data.data.result.semantics, document.getElementById("semantics_list"), "semantics");
            }

            if (route === "/tabs/process_items" && data.data?.result?.display_result && outputTextarea) {
                outputTextarea.value = data.data.result.display_result;
            }

            savePageState();
        } catch (err) {
            console.error(err);
            setError(err);
            savePageState();
        }
    }

    /* ========================================
       EVENT BINDINGS
    ======================================== */

    form?.addEventListener("submit", async (e) => {
        e.preventDefault();

        const input = document.getElementById("search_input")?.value ?? "";

        try {
            const data = await postJson(`/${prefix}`, {
                search_input: input,
            });

            setStatus(data.code, data.message, "");
            renderResults(data.data?.result, searchDiv);
            savePageState();

            form.reset();

            const savedState = getSavedState();
            if (inputTextarea) {
                inputTextarea.value = savedState?.inputText || "";
            }
        } catch (err) {
            setError(err);
            savePageState();
        }
    });

    addBtn?.addEventListener("click", () => {
        addSelectedToPanel("workspace", getSourceDivForAdd());
    });

    removeBtn?.addEventListener("click", () => {
        const activePanelId = getActivePanelId();
        const sourceContainer = getPanelListEl(activePanelId);

        if (!activePanelId || activePanelId === "search" || !sourceContainer) {
            setStatus(
                "REMOVE_FROM_PANEL_ERROR",
                "open a panel tab and highlight items to remove"
            );
            savePageState();
            return;
        }

        removeSelectedFromPanel(activePanelId, sourceContainer);
    });

    processBtn?.addEventListener("click", processSelectedItems);

    inputTextarea?.addEventListener("input", savePageState);
    instructionsTextarea?.addEventListener("input", savePageState);

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            const target = tab.dataset.tab;
            setActivePanel(target);
            animatePanelPopulate(target);
            savePageState();
        });
    });

    window.addEventListener("beforeunload", savePageState);
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") {
            savePageState();
        }
    });

    /* ========================================
       INIT
    ======================================== */

    restorePageState();
});