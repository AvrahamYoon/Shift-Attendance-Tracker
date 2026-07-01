(function () {
    document.addEventListener("DOMContentLoaded", function () {
        const form = document.getElementById("changelist-form");
        const dock = document.getElementById("attendance-delete-dock");
        if (!form || !dock) {
            return;
        }

        // Unfold also renders the default action dropdown; hide it on this page.
        const defaultActions = form.querySelector("#changelist-actions-wrapper");
        if (defaultActions) {
            defaultActions.remove();
        }

        const counter = dock.querySelector(".action-counter");
        const total = counter ? Number(counter.dataset.actionsIcnt || 0) : 0;

        function updateCounter() {
            if (!counter) {
                return;
            }
            const selected = form.querySelectorAll("input.action-select:checked").length;
            counter.textContent = selected + " of " + total + " selected";
        }

        form.addEventListener("change", function (event) {
            if (event.target && event.target.matches("input.action-select")) {
                updateCounter();
            }
        });

        updateCounter();
    });
})();
