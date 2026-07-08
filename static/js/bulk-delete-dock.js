(function () {
    document.addEventListener("DOMContentLoaded", function () {
        const form = document.getElementById("changelist-form");
        const dock = document.getElementById("bulk-delete-dock");
        if (!form || !dock) {
            return;
        }

        // Escape admin layout ancestors (transform/overflow break viewport fixed).
        document.body.appendChild(dock);

        const defaultActions = form.querySelector("#changelist-actions-wrapper");
        if (defaultActions) {
            const bar = defaultActions.closest("[class*='group-has-']");
            if (bar) {
                bar.remove();
            }
        }

        const counter = dock.querySelector(".action-counter");
        const deleteBtn = dock.querySelector(".bulk-delete-btn");
        const total = counter ? Number(counter.dataset.actionsIcnt || 0) : 0;

        function selectedCount() {
            return form.querySelectorAll("input.action-select:checked").length;
        }

        function updateCounter() {
            if (!counter) {
                return;
            }
            const selected = selectedCount();
            counter.textContent = selected + " of " + total + " selected";
        }

        function paginationOffset() {
            // Unfold sticky footer: .lg:sticky.lg:bottom-0 border-t
            const sticky = document.querySelector(
                "#footer .lg\\:sticky, footer .lg\\:sticky, .lg\\:sticky.lg\\:bottom-0"
            );
            if (!sticky) {
                return 80;
            }
            const height = sticky.getBoundingClientRect().height || 64;
            return Math.ceil(height) + 12;
        }

        function placeDock() {
            dock.style.bottom = paginationOffset() + "px";
            dock.style.right = "1.5rem";
            dock.style.left = "auto";
            dock.style.top = "auto";
            dock.style.zIndex = "9999";
            dock.style.position = "fixed";
        }

        function syncDock() {
            const selected = selectedCount();
            const show = selected > 0;
            dock.classList.toggle("hidden", !show);
            dock.classList.toggle("flex", show);
            if (show) {
                placeDock();
            }
            updateCounter();
        }

        if (deleteBtn) {
            deleteBtn.addEventListener("click", function (event) {
                event.preventDefault();
                if (selectedCount() === 0) {
                    return;
                }
                let actionInput = form.querySelector(
                    'input[type="hidden"][name="action"]'
                );
                if (!actionInput) {
                    actionInput = document.createElement("input");
                    actionInput.type = "hidden";
                    actionInput.name = "action";
                    form.appendChild(actionInput);
                }
                actionInput.value = "delete_selected";
                form.requestSubmit ? form.requestSubmit() : form.submit();
            });
        }

        form.addEventListener("change", function (event) {
            const target = event.target;
            if (!target) {
                return;
            }
            if (
                target.matches("input.action-select") ||
                target.id === "action-toggle"
            ) {
                syncDock();
            }
        });

        window.addEventListener("resize", function () {
            if (!dock.classList.contains("hidden")) {
                placeDock();
            }
        });

        syncDock();
    });
})();
