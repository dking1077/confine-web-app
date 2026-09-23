const PREFIX = "search";
const PAGE_STATE_KEY = "index_page_state_v1";

document.addEventListener("DOMContentLoaded", () => {
    // --- 1. DOM Elements ---
    const form = document.getElementById("search_form");
    const searchInput = document.getElementById("search_input");
    const modeSelect = document.getElementById("mode_select");

    const resultsDiv = document.getElementById("results");
    const searchDiv = document.getElementById("search");
    const workspaceDiv = document.getElementById("workspace_list");
    const favoritesSearchDiv = document.getElementById("favorites_search");

    const inputTextarea = document.getElementById("input_textarea");
    const instructionsTextarea = document.getElementById("instructions_textarea");
    const outputTextarea = document.getElementById("output_textarea");

    const addBtn = document.getElementById("add_btn");
    const removeBtn = document.getElementById("remove_btn");
    const processBtn = document.getElementById("process_btn");

    const tabs = document.querySelectorAll(".tab");
    const panels = document.querySelectorAll(".panel");

    // --- 2. Helper Utilities ---
    const getToken = () => localStorage.getItem("access_token");

    function getActivePanelId() {
        const activePanel = document.querySelector(".panel.active");
        return activePanel ? activePanel.id : "search";
    }

    function getPanelListEl(panelId) {
        if (!panelId) return null;
        if (panelId === "workspace") return workspaceDiv;
        return document.getElementById(`${panelId}_list`);
    }

    function getSelectedIds(container) {
        if (!container) return [];
        const selectedElements = container.querySelectorAll(".selectable-item.selected");
        return Array.from(selectedElements).map(el => el.dataset.id).filter(Boolean);
    }

    function clearSelectedItems(container) {
        if (!container) return;
        container.querySelectorAll(".selectable-item.selected").forEach(el => {
            el.classList.remove("selected");
        });
    }

    function setStatus(code, message, details = "") {
        if (!resultsDiv) return;
        const detailsText = typeof details === "object" ? JSON.stringify(details) : details;
        let html = `code: ${code} &nbsp; message: ${message}`;
        if (detailsText) html += ` &nbsp; details: ${detailsText}`;
        resultsDiv.innerHTML = html;
    }

    function setError(err) {
        if (!resultsDiv) return;
        const detailMsg = err.details ? `<br><small>${JSON.stringify(err.details)}</small>` : "";
        resultsDiv.innerHTML = `<p style="color:red;">Error: ${err.message || String(err)}${detailMsg}</p>`;
    }

    // --- 3. Page State (Session Storage) ---
    function savePageState() {
        const state = {
            resultsHTML: resultsDiv?.innerHTML || "",
            searchHTML: searchDiv?.innerHTML || "",
            workspaceHTML: workspaceDiv?.innerHTML || "",
            inputText: inputTextarea?.value || "",
            instructionsText: instructionsTextarea?.value || "",
            outputText: outputTextarea?.value || "",
            activePanel: getActivePanelId()
        };
        sessionStorage.setItem(PAGE_STATE_KEY, JSON.stringify(state));
    }

    function restorePageState() {
        const raw = sessionStorage.getItem(PAGE_STATE_KEY);
        if (!raw) return;

        try {
            const state = JSON.parse(raw);

            if (resultsDiv) resultsDiv.innerHTML = state.resultsHTML || "";
            if (searchDiv) searchDiv.innerHTML = state.searchHTML || "";
            if (workspaceDiv) workspaceDiv.innerHTML = state.workspaceHTML || "";
            if (inputTextarea) inputTextarea.value = state.inputText || "";
            if (instructionsTextarea) instructionsTextarea.value = state.instructionsText || "";
            if (outputTextarea) outputTextarea.value = state.outputText || "";

            setActivePanel(state.activePanel || "search");
            rebindRestoredEvents();
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

        const listIds = ["concepts", "semantics", "instructions", "input", "output", "favorites_search"];
        listIds.forEach(id => {
            const el = document.getElementById(id.endsWith("_search") ? id : `${id}_list`);
            if (el) el.innerHTML = "";
        });

        setActivePanel("search");
    }
    window.clearIndexUI = clearIndexUI;

    // --- 4. Navigation & UI Interactivity ---
    function setActivePanel(panelId) {
        tabs.forEach(tab => tab.classList.toggle("active", tab.dataset.tab === panelId));
        panels.forEach(panel => panel.classList.toggle("active", panel.id === panelId));
    }

    function toggleSelected(el) {
        el.classList.toggle("selected");
        savePageState();
    }

    function createSelectableResult(text, dataset = {}) {
        const div = document.createElement("div");
        div.className = "search-result-item selectable-item";
        div.textContent = text;

        Object.entries(dataset).forEach(([key, value]) => {
            div.dataset[key] = value;
        });

        div.addEventListener("click", () => toggleSelected(div));
        return div;
    }

    function bindLyricsToggle(toggleBtn) {
        toggleBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const wrapper = toggleBtn.closest(".workspace-item");
            const lyricsBox = wrapper?.querySelector(".lyrics-box");
            if (!lyricsBox) return;

            const isOpen = lyricsBox.style.display === "block";
            lyricsBox.style.display = isOpen ? "none" : "block";
            toggleBtn.classList.toggle("open", !isOpen);
            toggleBtn.textContent = isOpen ? "<" : "v";
            savePageState();
        });
    }

    function rebindRestoredEvents() {
        document.querySelectorAll(".panel .selectable-item").forEach(item => {
            item.addEventListener("click", () => toggleSelected(item));
        });

        workspaceDiv?.querySelectorAll(".lyrics-toggle").forEach(bindLyricsToggle);
    }

    // --- 5. Animations ---
    function animatePanelPopulate(panelId) {
        let items = [];
        if (panelId === "search") {
            items = Array.from(searchDiv?.querySelectorAll(".search-result-item") || []);
        } else if (panelId === "workspace") {
            items = Array.from(workspaceDiv?.querySelectorAll(".workspace-item") || []);
        } else if (panelId === "concepts" || panelId === "semantics") {
            const listEl = document.getElementById(`${panelId}_list`);
            items = Array.from(listEl?.querySelectorAll(".search-result-item") || []);
        }

        items.forEach((el, index) => {
            el.classList.remove("item-populate");
            el.style.animationDelay = `${index * 45}ms`;

            requestAnimationFrame(() => el.classList.add("item-populate"));

            el.addEventListener("animationend", () => {
                el.classList.remove("item-populate");
                el.style.animationDelay = "";
            }, { once: true });
        });
    }

    // --- 6. Network Requests (API) ---
    async function parseJsonOrThrow(response) {
        const text = await response.text();
        const contentType = response.headers.get("content-type") || "";

        if (!contentType.includes("application/json")) {
            const preview = text.slice(0, 220).replace(/\s+/g, " ");
            throw new Error(`Expected JSON, got ${contentType || "unknown"} (status ${response.status}). Body: ${preview}`);
        }

        let data;
        try {
            data = JSON.parse(text);
        } catch {
            throw new Error(`Invalid JSON (status ${response.status})`);
        }

        if (!response.ok) {
            const err = new Error(data?.message || `Request failed with status ${response.status}`);
            err.details = data?.details || null;
            err.code = data?.code || "ERROR";
            throw err;
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
                ...(token && { Authorization: `Bearer ${token}` })
            },
            body: JSON.stringify(body)
        });
        return parseJsonOrThrow(response);
    }

    async function pollTaskStatus(jobId, endpointPrefix = PREFIX) {
        const token = getToken();

        while (true) {
            const response = await fetch(`/${endpointPrefix}/status/${jobId}`, {
                headers: {
                    ...(token && { Authorization: `Bearer ${token}` })
                }
            });

            const data = await parseJsonOrThrow(response);
            const payload = data.data ?? data;
            const status = payload.status || data.status;

            if (status === "SUCCESS") return data;

            if (status === "FAILURE") {
                const errDetail = data.details?.error || data.message || "Background task failed";
                const err = new Error(`Task failed: ${errDetail}`);
                err.details = data.details || null;
                throw err;
            }

            setStatus(data.code || "TASK_IN_PROGRESS", "Task in progress...", `job_id: ${jobId}`);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }

    // --- 7. Rendering Functions ---
    function renderResults(data, container) {
        if (!container) return;
        container.innerHTML = "";

        if (!Array.isArray(data) || data.length === 0) {
            container.textContent = "No results";
            return;
        }

        data.forEach(item => {
            const featuresText = item.features?.length ? ` feat. ${item.features.join(", ")}` : "";
            const label = `${item.artist_name} - ${item.track_name}${featuresText}`;

            const element = createSelectableResult(label, {
                id: item.commontrack_id,
                artist: item.artist_name,
                track: item.track_name
            });
            container.appendChild(element);
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

        data.forEach(item => {
            const artist = item.artist_name ? `${item.artist_name} - ` : "";
            const track = item.track_name || item.name || "item";

            const element = createSelectableResult(`${artist}${track}`, {
                id: item.commontrack_id || item.id || ""
            });
            container.appendChild(element);
        });
    }

    function renderAnalyzePanel(groups, container, type) {
        if (!container) return;
        container.innerHTML = "";

        if (!Array.isArray(groups) || groups.length === 0) {
            container.textContent = "No data";
            return;
        }

        groups.forEach(trackGroup => {
            const items = Array.isArray(trackGroup[type]) ? trackGroup[type] : [];
            items.forEach(item => {
                const isConcept = type === "concepts";
                const title = isConcept
                    ? (item.display_concept || item.name || "concept")
                    : (item.display_semantic || item.name || "semantic");
                const evidence = item.evidence ? `\n"${item.evidence}"` : "";

                const element = createSelectableResult(`${title}${evidence}`, {
                    id: String(item.id || ""),
                    commontrackId: String(trackGroup.commontrack_id || ""),
                    track: trackGroup.track || "",
                    kind: type
                });
                container.appendChild(element);
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

        data.forEach(item => {
            const wrapper = document.createElement("div");
            wrapper.className = "workspace-item";
            wrapper.dataset.id = item.commontrack_id;
            wrapper.dataset.artist = item.artist_name;
            wrapper.dataset.track = item.track_name;

            wrapper.innerHTML = `
                <div class="workspace-header">
                    <div class="workspace-title selectable-item" 
                         data-id="${item.commontrack_id}" 
                         data-artist="${item.artist_name}" 
                         data-track="${item.track_name}">
                        ${item.artist_name} - ${item.track_name}
                    </div>
                    <button type="button" class="lyrics-toggle" aria-label="Toggle lyrics">&lt;</button>
                </div>
                <div class="lyrics-box" style="display: none;">
                    ${item.lyrics || "No lyrics available"}
                </div>
            `;

            // Bind click listeners for newly generated elements
            const titleEl = wrapper.querySelector(".workspace-title");
            titleEl.addEventListener("click", () => toggleSelected(titleEl));

            const toggleBtn = wrapper.querySelector(".lyrics-toggle");
            bindLyricsToggle(toggleBtn);

            container.appendChild(wrapper);
        });

        animatePanelPopulate("workspace");
    }

    // --- 8. Panel Actions ---
    async function addSelectedToPanel(targetPanel, sourceContainer) {
        const trackIds = getSelectedIds(sourceContainer);

        if (trackIds.length === 0) {
            setStatus("ADD_TO_PANEL_ERROR", "no tracks selected");
            savePageState();
            return;
        }

        try {
            const data = await postJson("/tabs/add_to_panel", {
                panel: targetPanel,
                items: trackIds
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
        const itemIds = getSelectedIds(sourceContainer);

        if (itemIds.length === 0) {
            setStatus("REMOVE_FROM_PANEL_ERROR", "no items selected");
            savePageState();
            return;
        }

        try {
            const data = await postJson("/tabs/remove_from_panel", {
                panel: targetPanel,
                items: itemIds
            });

            setStatus(data.code, data.message, "items removed");

            const targetContainer = getPanelListEl(targetPanel);
            if (targetContainer) {
                const results = data.data?.result;
                if (targetPanel === "workspace") renderWorkspace(results, targetContainer);
                else if (targetPanel === "concepts") renderAnalyzePanel(results, targetContainer, "concepts");
                else if (targetPanel === "semantics") renderAnalyzePanel(results, targetContainer, "semantics");
                else renderGenericPanel(results, targetContainer);
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
        const trackIds = getSelectedIds(workspaceDiv);
        const conceptIds = getSelectedIds(document.getElementById("concepts_list"));
        const semanticIds = getSelectedIds(document.getElementById("semantics_list"));

        if (trackIds.length === 0) {
            setStatus("PROCESS_ITEMS_ERROR", "no tracks selected in workspace");
            savePageState();
            return;
        }

        const mode = (modeSelect?.value || "Transform").toLowerCase();
        const route = mode === "analyze" ? "/tabs/analyze_items" : "/tabs/process_items";

        try {
            const data = await postJson(route, {
                items: trackIds,
                concept_ids: conceptIds,
                semantic_ids: semanticIds,
                instructions: instructionsTextarea?.value || "",
                input_text: inputTextarea?.value || ""
            });

            const jobId = data.data?.job_id || data.job_id;
            if (!jobId) throw new Error("No job_id returned from request.");

            setStatus(data.code, data.message, `job_id: ${jobId}`);

            const finalData = await pollTaskStatus(jobId, "tabs");
            const result = finalData.data?.result || finalData.result;

            setStatus(finalData.code || "SUCCESS", finalData.message || "Completed", "");

            if (route === "/tabs/analyze_items" && result) {
                renderAnalyzePanel(result.concepts, document.getElementById("concepts_list"), "concepts");
                renderAnalyzePanel(result.semantics, document.getElementById("semantics_list"), "semantics");
            }

            if (route === "/tabs/process_items" && result?.display_result && outputTextarea) {
                outputTextarea.value = result.display_result;
            }

            savePageState();
        } catch (err) {
            console.error(err);
            setError(err);
            savePageState();
        }
    }

    // --- 9. Event Listeners ---
    form?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const query = searchInput?.value ?? "";

        try {
            const data = await postJson(`/${PREFIX}/`, { search_input: query });

            const jobId = data.data?.job_id || data.data?.task_id || data.data?.id || data.job_id || data.task_id || data.id;

            if (!jobId) {
                throw new Error(`No job_id returned from search request. Response: ${JSON.stringify(data)}`);
            }

            setStatus(data.code || "SEARCH_STARTED", data.message || "Search started", `job_id: ${jobId}`);

            const finalData = await pollTaskStatus(jobId, PREFIX);
            setStatus(finalData.code || "SUCCESS", finalData.message || "Search complete", "");

            const results = finalData.data?.result || finalData.data?.results || finalData.result || finalData.data;
            renderResults(results, searchDiv);
            savePageState();

            form.reset();

            const savedState = JSON.parse(sessionStorage.getItem(PAGE_STATE_KEY) || "{}");
            if (inputTextarea) {
                inputTextarea.value = savedState.inputText || "";
            }
        } catch (err) {
            setError(err);
            savePageState();
        }
    });

    addBtn?.addEventListener("click", () => {
        const activeId = getActivePanelId();
        const source = (activeId === "favorites_search" && favoritesSearchDiv) ? favoritesSearchDiv : searchDiv;
        addSelectedToPanel("workspace", source);
    });

    removeBtn?.addEventListener("click", () => {
        const activePanelId = getActivePanelId();
        const sourceContainer = getPanelListEl(activePanelId);

        if (!activePanelId || activePanelId === "search" || !sourceContainer) {
            setStatus("REMOVE_FROM_PANEL_ERROR", "open a panel tab and highlight items to remove");
            savePageState();
            return;
        }

        removeSelectedFromPanel(activePanelId, sourceContainer);
    });

    processBtn?.addEventListener("click", processSelectedItems);

    inputTextarea?.addEventListener("input", savePageState);
    instructionsTextarea?.addEventListener("input", savePageState);

    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            const targetPanel = tab.dataset.tab;
            setActivePanel(targetPanel);
            animatePanelPopulate(targetPanel);
            savePageState();
        });
    });

    window.addEventListener("beforeunload", savePageState);
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") {
            savePageState();
        }
    });

    // --- 10. Initial Load ---
    restorePageState();
});