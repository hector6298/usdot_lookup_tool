import { Engagement } from "./update_carrier_engagement.js";

const Filters = {
    offset: 0,
    limit: 10,
    isLoading: false,
    hasMoreData: true,

    // Fetch data with filters and lazy loading
    fetchData: async function (append = false) {
        if (Filters.isLoading || !Filters.hasMoreData) return;

        Filters.isLoading = true;

        const form = document.getElementById("filter-form");
        const tableType = form.getAttribute("data-dashboard-type"); // Get table type

        // From data gives us the carrier_contacted and carrier_interested values
        const formData = new FormData(form);
        const queryParams = new URLSearchParams();

        for (const [key, value] of formData.entries()) {
            if (value.trim() !== "") {
                queryParams.append(key, value);
            }
        }

        queryParams.append("offset", Filters.offset);
        queryParams.append("limit", Filters.limit);

        try {
            const response = await fetch(`/data/fetch/${tableType}?${queryParams}`, {
                method: "GET",
                headers: { "Accept": "application/json" },
            });

            if (response.ok) {
                const data = await response.json();

                if (data.length < Filters.limit) {
                    Filters.hasMoreData = false; // No more data to load
                }

                if (append) {
                    Filters.appendRows(data, tableType); // Pass table type
                } else {
                    Filters.updateTable(data, tableType); // Pass table type
                }

                // Update the offset for the next batch
                Filters.offset += Filters.limit;
            } else {
                console.error("Failed to fetch data");
            }
        } catch (error) {
            console.error("Error fetching data:", error);
        } finally {
            Filters.isLoading = false;
        }
    },

    // Update the table (replace all rows)
    updateTable: function (data, tableType) {
        const tbody = document.querySelector("table tbody");
        tbody.innerHTML = ""; // Clear existing rows
        Filters.appendRows(data, tableType); // Append new rows
    },

    // Append rows to the table
    appendRows: function (data, tableType) {
        const tbody = document.querySelector("table tbody");

        if (!RowTemplates[tableType]) {
            console.error(`No row template found for table type: ${tableType}`);
            return;
        }

        data.forEach((item) => {
            const row = RowTemplates[tableType](item); // Use the appropriate row template
            tbody.insertAdjacentHTML("beforeend", row);
        });

        // Reinitialize checkboxes for engagement tracking
        if (tableType === "carriers") {
            Engagement.reinitializeInputs();
        }
    },

    // Handle filter form submission
    handleFilterFormSubmit: function (event) {
        event.preventDefault();

        // Reset state for new filter results
        Filters.offset = 0;
        Filters.hasMoreData = true;

        // Fetch filtered data and replace the table
        Filters.fetchData(false);
    },

    // Handle infinite scrolling
    handleScroll: function () {
        const container = document.getElementById("scrollable-container");
        if (container.scrollTop + container.clientHeight >= container.scrollHeight) {
            Filters.fetchData(true); // Append new data
        }
    },

    // Initialize the script
    init: function () {
        // Attach filter form submission handler
        const filterForm = document.getElementById("filter-form");
        if (filterForm) {
            filterForm.addEventListener("submit", Filters.handleFilterFormSubmit);
        }

        // Attach scroll event handler
        const container = document.getElementById("scrollable-container");
        if (container) {
            container.addEventListener("scroll", Filters.handleScroll);
        }

        // Select all functionality
        const selectAll = document.getElementById("select-all");
        if (selectAll) {
            selectAll.addEventListener("change", function () {
                const checked = this.checked;
                document.querySelectorAll(".carrier-select").forEach(cb => cb.checked = checked);
            });
        }

        // Sync to Salesforce button
        const syncBtn = document.getElementById("sync-to-salesforce");
        if (syncBtn) {
            syncBtn.addEventListener("click", async function () {
                const selected = Array.from(document.querySelectorAll(".carrier-select:checked"))
                    .map(cb => cb.getAttribute("data-usdot"));
                if (selected.length === 0) {
                    alert("Please select at least one carrier to sync.");
                    return;
                }
                const response = await fetch("/salesforce/upload_carriers", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ carriers_usdot: selected })
                });
                if (response.ok) {
                    alert("Sync request sent!");
                    // Optionally, reload table data here
                    Filters.offset = 0;
                    Filters.hasMoreData = true;
                    Filters.fetchData(false);
                } else {
                    alert("Failed to sync to Salesforce.");
                }
            });
        }

        // Load the initial batch of data
        Filters.fetchData(false);
    },
    
};

// Row templates for different table types
const RowTemplates = {
    carriers: function (carrier) {
        return `
            <tr>
            <td>
                <input type="checkbox" class="carrier-select" data-usdot="${carrier.usdot}">
            </td>
            <td><a href="/dashboards/carrier_details/${carrier.usdot}" class="dot-link">${carrier.usdot}</a></td>
            <td>${carrier.legal_name}</td>
            <td>${carrier.phone}</td>
            <td>${carrier.mailing_address}</td>
            <td>${carrier.created_at}</td>
            <td><input type="checkbox" class="form-check-input checkbox-track" 
            data-usdot="${carrier.usdot}" 
            data-field="carrier_contacted"
            ${carrier.carrier_contacted ? "checked" : ""}>
            </td>
            <td><input type="checkbox" class="form-check-input checkbox-track" 
            data-usdot="${carrier.usdot}" 
            data-field="carrier_followed_up"
            ${carrier.carrier_followed_up ? "checked" : ""}>
            </td>
            <td>
            ${carrier.carrier_contacted ? 
                `<input type="date" class="form-control checkbox-track" 
                data-usdot="${carrier.usdot}" 
                data-field="carrier_follow_up_by_date"
                value="${carrier.carrier_follow_up_by_date}">` 
                : "Carrier not Contacted"}
            </td>
            <td><input type="checkbox" class="form-check-input checkbox-track" 
            data-usdot="${carrier.usdot}" 
            data-field="carrier_interested"
            ${carrier.carrier_interested ? "checked" : ""}>
            </td>
            <td>${carrier.in_salesforce ? "Yes" : "No"}</td>
            <td>${carrier.salesforce_synced_at ? carrier.salesforce_synced_at : ""}</td>
            </tr>
        `;
    },
    lookup_history: function (history) {
        return `
            <tr>
                <td><a href="/dashboards/carrier_details/${history.dot_reading}" class="dot-link">${history.dot_reading}</a></td>
                <td>${history.legal_name}</td>
                <td>${history.phone}</td>
                <td>${history.mailing_address}</td>
                <td>${history.timestamp}</td>
                <td>${history.filename}</td>
                <td>${history.user_id}</td>
                <td>${history.org_id}</td>
            </tr>
        `;
    },
};

// Initialize the Filters module when the DOM is ready
document.addEventListener("DOMContentLoaded", Filters.init);