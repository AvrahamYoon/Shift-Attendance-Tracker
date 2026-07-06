(function () {
    document.addEventListener("DOMContentLoaded", function () {
        const form = document.getElementById("changelist-form");
        const dock = document.getElementById("attendance-delete-dock");
        if (!form || !dock) {
            return;
        }

        const defaultActions = form.querySelector("#changelist-actions-wrapper");
        if (defaultActions) {
            defaultActions.closest("[class*='group-has-']")?.remove();
        }

        const counter = dock.querySelector(".action-counter");
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

        function syncDock() {
            const selected = selectedCount();
            const show = selected > 0;
            dock.classList.toggle("hidden", !show);
            dock.classList.toggle("flex", show);
            updateCounter();
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

        syncDock();
    });
})();
