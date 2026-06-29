// Canteen Management - POS Customization (v3 - Page toolbar approach)
// Adds employee wallet selector, table management, and balance display
// to ERPNext v15 POS interface.
//
// Strategy:
//   1. Add buttons to the POS page toolbar via page.add_action_item() — always works,
//      survives Vue re-renders because toolbar is outside the Vue render tree
//   2. Floating widget fallback if page toolbar isn't available
//   3. frappe.ui.form.on for customer change auto-detection

frappe.provide("canteen_management.pos");

canteen_management.pos = {
    employee_dialog: null,
    table_dialog: null,
    pos_frm: null,
    _employee_btn: null,
    _table_btn: null,

    // ========== bootstrap ==========

    init: function () {
        console.log("[Canteen POS] Initializing...");
        var self = this;

        // Register form events (fire in POS because frm.set_value triggers them)
        frappe.ui.form.on("POS Invoice", {
            refresh: function (frm) {
                self.pos_frm = frm;
                // Reset table button if no table assigned (new invoice or after submit)
                if (!frm.doc.canteen_table) {
                    self._update_table_btn_text("Table — None");
                    $("#canteen-floating-table-btn").html("🍽️ Select Table");
                }
            },
            customer: function (frm) {
                self.pos_frm = frm;
                self.on_customer_change(frm, frm.doc.customer);
            },
        });

        // Add toolbar buttons + wait for page to be ready
        this._add_toolbar_buttons();
    },

    // ========== page toolbar buttons (PRIMARY) ==========

    _add_toolbar_buttons: function () {
        var self = this;
        var attempts = 0;

        var try_add = function () {
            attempts++;

            var page = frappe.pages["point-of-sale"];
            if (page && page.add_action_item) {
                console.log("[Canteen POS] Adding toolbar buttons via page.add_action_item");
                // Employee button
                self._employee_btn = page.add_action_item(
                    "👤 Employee",
                    function () {
                        self.open_employee_dialog();
                    },
                    { icon: "user" }
                );
                $(self._employee_btn).attr("id", "canteen-employee-btn").css("margin-right", "4px");

                // Table button
                self._table_btn = page.add_action_item(
                    "🍽️ Table — None",
                    function () {
                        self.open_table_dialog();
                    },
                    { icon: "table" }
                );
                $(self._table_btn).attr("id", "canteen-table-btn");
                return;
            }

            // Try page.page.add_action_item
            if (page && page.page && page.page.add_action_item) {
                console.log("[Canteen POS] Adding toolbar buttons via page.page.add_action_item");
                self._employee_btn = page.page.add_action_item(
                    "👤 Employee",
                    function () {
                        self.open_employee_dialog();
                    },
                    { icon: "user" }
                );
                $(self._employee_btn).attr("id", "canteen-employee-btn").css("margin-right", "4px");

                self._table_btn = page.page.add_action_item(
                    "🍽️ Table — None",
                    function () {
                        self.open_table_dialog();
                    },
                    { icon: "table" }
                );
                $(self._table_btn).attr("id", "canteen-table-btn");
                return;
            }

            if (attempts < 15) {
                setTimeout(try_add, 1000); // retry every 1s for 15s
            } else {
                console.log("[Canteen POS] Page toolbar unavailable, using floating widget");
                self._create_floating_widget();
            }
        };

        try_add();
    },

    // ========== floating widget fallback ==========

    _create_floating_widget: function () {
        if ($("#canteen-pos-floating-widget").length) return;

        var self = this;
        var html =
            '<div id="canteen-pos-floating-widget" style="position:fixed;bottom:80px;right:20px;z-index:1000;display:flex;flex-direction:column;gap:8px;">' +
            '    <button class="btn btn-primary btn-sm" id="canteen-floating-btn" style="border-radius:20px;padding:10px 18px;box-shadow:0 4px 12px rgba(0,0,0,0.15);">' +
            '        <span>👤 Select Employee</span>' +
            '        <span id="canteen-floating-badge" style="display:none;margin-left:6px;background:#fff;color:#28a745;border-radius:10px;padding:1px 7px;font-weight:600;">₹0</span>' +
            "    </button>" +
            '    <button class="btn btn-success btn-sm" id="canteen-floating-table-btn" style="border-radius:20px;padding:10px 18px;box-shadow:0 4px 12px rgba(0,0,0,0.15);">' +
            '        <span>🍽️ Select Table</span>' +
            "    </button>" +
            "</div>";

        $("body").append(html);
        $("#canteen-floating-btn").on("click", function () {
            self.open_employee_dialog();
        });
        $("#canteen-floating-table-btn").on("click", function () {
            self.open_table_dialog();
        });
        console.log("[Canteen POS] Floating widget created");
    },

    // ========== employee selection dialog ==========

    open_employee_dialog: function () {
        var self = this;

        if (this.employee_dialog) {
            this.employee_dialog.set_value("employee", "");
            this.employee_dialog.set_value("balance", null);
            this.employee_dialog.set_value("credit_limit", null);
            this.employee_dialog.set_df_property("balance_html", "options", "");
            this.employee_dialog.show();
            return;
        }

        this.employee_dialog = new frappe.ui.Dialog({
            title: "Select Canteen Employee",
            fields: [
                {
                    fieldtype: "Link",
                    fieldname: "employee",
                    label: "Employee",
                    options: "Employee",
                    reqd: 1,
                    description: "Select the employee whose wallet will be charged",
                    change: function () {
                        var emp = this.get_value();
                        if (emp) self.fetch_and_show_balance(emp);
                    },
                },
                {
                    fieldtype: "HTML",
                    fieldname: "balance_html",
                    label: "Wallet Balance",
                },
                {
                    fieldtype: "Currency",
                    fieldname: "balance",
                    label: "Balance",
                    read_only: 1,
                    depends_on: "eval:doc.employee",
                },
                {
                    fieldtype: "Currency",
                    fieldname: "credit_limit",
                    label: "Credit Limit",
                    read_only: 1,
                    depends_on: "eval:doc.employee",
                },
            ],
            primary_action_label: "Select Employee",
            primary_action: function (values) {
                if (values.employee) {
                    self.set_employee(values.employee);
                    self.employee_dialog.hide();
                }
            },
        });

        this.employee_dialog.show();
    },

    // ========== fetch wallet balance ==========

    fetch_and_show_balance: function (employee) {
        var self = this;
        if (!self.employee_dialog) return;

        frappe.call({
            method: "canteen_management.api.get_wallet_balance",
            args: { employee: employee },
            callback: function (r) {
                if (r.message && r.message.balance != null) {
                    var bal = Number(r.message.balance).toFixed(2);
                    var credit = Number(r.message.credit_limit || 0).toFixed(2);
                    var avail = (
                        Number(r.message.balance) +
                        Number(r.message.credit_limit || 0)
                    ).toFixed(2);

                    self.employee_dialog.set_value("balance", bal);
                    self.employee_dialog.set_value("credit_limit", credit);
                    self.employee_dialog.set_df_property(
                        "balance_html",
                        "options",
                        '<div class="alert alert-success" style="margin:5px 0;padding:10px;">' +
                            "<strong>Wallet Balance: ₹" +
                            bal +
                            "</strong><br>" +
                            "<small>Available: ₹" +
                            avail +
                            " (including ₹" +
                            credit +
                            " credit)</small></div>"
                    );
                    self.employee_dialog.refresh_field("balance_html");
                } else {
                    self.employee_dialog.set_value("balance", 0);
                    self.employee_dialog.set_value("credit_limit", 0);
                    self.employee_dialog.set_df_property(
                        "balance_html",
                        "options",
                        '<div class="alert alert-warning" style="margin:5px 0;padding:10px;">No active wallet found for this employee</div>'
                    );
                    self.employee_dialog.refresh_field("balance_html");
                }
            },
        });
    },

    // ========== set employee on invoice ==========

    set_employee: function (employee) {
        var frm = this.pos_frm;
        if (!frm) {
            frappe.show_alert({
                message: "POS form not ready. Cannot set employee.",
                indicator: "red",
            });
            return;
        }

        var self = this;

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Employee",
                filters: { name: employee },
                fieldname: ["employee_name"],
            },
            callback: function (r) {
                var emp_name = employee;
                if (r.message) emp_name = r.message.employee_name || employee;

                // Set on the POS Invoice document
                frm.set_value("canteen_employee", employee);

                // Update toolbar button text
                self._update_button_text(emp_name, employee);

                // Fetch and show wallet balance
                self._update_wallet_display(employee, emp_name);

                frappe.show_alert({
                    message: "Employee set: " + emp_name,
                    indicator: "green",
                });
            },
        });
    },

    _update_button_text: function (emp_name, employee) {
        var btn_html = "👤 " + emp_name + ' <span class="badge" id="canteen-balance-badge">...</span>';
        if (this._employee_btn) {
            $(this._employee_btn).html(btn_html);
        } else {
            $("#canteen-employee-btn").html(btn_html);
        }
    },

    _update_table_btn_text: function (table_name) {
        var btn_html = "🍽️ " + table_name;
        if (this._table_btn) {
            $(this._table_btn).html(btn_html);
        } else {
            $("#canteen-table-btn").html(btn_html);
        }
    },

    _update_wallet_display: function (employee, emp_name) {
        var self = this;

        frappe.call({
            method: "canteen_management.api.get_wallet_balance",
            args: { employee: employee },
            callback: function (r) {
                if (r.message && r.message.balance != null) {
                    var bal = Number(r.message.balance).toFixed(2);
                    var badge_html =
                        '<span class="badge" style="background:' +
                        (r.message.balance > 0 ? "#28a745" : "#ffc107") +
                        ";color:#fff;\">₹" +
                        bal +
                        "</span>";
                    $("#canteen-employee-btn").html("👤 " + emp_name + " " + badge_html);

                    // Also update floating badge
                    var $fb = $("#canteen-floating-badge");
                    if ($fb.length) {
                        $fb.text("₹" + bal).show();
                    }
                } else {
                    var badge_html =
                        '<span class="badge" style="background:#dc3545;color:#fff;">No wallet</span>';
                    $("#canteen-employee-btn").html("👤 " + emp_name + " " + badge_html);
                }
            },
        });
    },

    // ========== customer change auto-detect ==========

    on_customer_change: function (frm, customer) {
        if (!customer) return;

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Employee",
                filters: { customer: customer },
                fieldname: ["name", "employee_name"],
            },
            callback: function (r) {
                if (r.message) {
                    canteen_management.pos.set_employee(r.message.name);
                }
            },
        });
    },

    // ========== table selection dialog ==========

    open_table_dialog: function () {
        var self = this;

        if (self.table_dialog) {
            self.table_dialog.show();
            self._refresh_table_grid();
            return;
        }

        self.table_dialog = new frappe.ui.Dialog({
            title: "Select Table",
            fields: [
                {
                    fieldtype: "HTML",
                    fieldname: "table_grid",
                    label: "Tables",
                },
            ],
        });

        self.table_dialog.show();

        // Show loading and fetch tables
        self.table_dialog.set_df_property(
            "table_grid",
            "options",
            '<div class="text-center text-muted" style="padding:30px;">Loading tables...</div>'
        );
        self._refresh_table_grid();
    },

    _refresh_table_grid: function () {
        var self = this;

        frappe.call({
            method: "canteen_management.api.get_tables",
            callback: function (r) {
                if (r.message && self.table_dialog) {
                    var html = self._render_table_grid(r.message);
                    self.table_dialog.set_df_property("table_grid", "options", html);
                }
            },
        });
    },

    _render_table_grid: function (tables) {
        var self = this;

        if (!tables || tables.length === 0) {
            return '<div class="alert alert-info text-center" style="margin:10px;">No tables found. Create tables in Canteen Table master.</div>';
        }

        var html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;padding:5px;">';

        for (var i = 0; i < tables.length; i++) {
            var t = tables[i];
            var status = (t.status || "Available").toLowerCase();
            var selected = self.pos_frm && self.pos_frm.doc.canteen_table === t.name;

            // Color mapping
            var bgColor, textColor, statusLabel, borderStyle;
            switch (status) {
                case "available":
                    bgColor = selected ? "#d4edda" : "#e8f5e9";
                    textColor = "#155724";
                    statusLabel = "Available";
                    borderStyle = selected ? "3px solid #28a745" : "1px solid #c3e6cb";
                    break;
                case "occupied":
                    bgColor = "#f8d7da";
                    textColor = "#721c24";
                    statusLabel = "Occupied";
                    borderStyle = "1px solid #f5c6cb";
                    break;
                case "reserved":
                    bgColor = "#fff3cd";
                    textColor = "#856404";
                    statusLabel = "Reserved";
                    borderStyle = "1px solid #ffeeba";
                    break;
                case "cleaning":
                    bgColor = "#e2e3e5";
                    textColor = "#383d41";
                    statusLabel = "Cleaning";
                    borderStyle = "1px solid #d6d8db";
                    break;
                default:
                    bgColor = "#f8f9fa";
                    textColor = "#333";
                    statusLabel = status;
                    borderStyle = "1px solid #dee2e6";
            }

            var displayName = t.table_name || t.name || t.table_number || "Table";
            var capacity = t.capacity ? "👤" + t.capacity : "";
            var locationLabel = t.location ? '<br><small style="opacity:0.7;">📍' + t.location + "</small>" : "";

            // Disable click for non-available tables unless it's already selected
            var clickable = status === "available" || selected;
            var cursorStyle = clickable ? "cursor:pointer;" : "cursor:not-allowed;opacity:0.6;";

            html +=
                '<div onclick="' +
                (clickable ? "canteen_management.pos.select_table('" + t.name + "')" : "") +
                '" style="background:' +
                bgColor +
                ";color:" +
                textColor +
                ";border:" +
                borderStyle +
                ";border-radius:10px;padding:12px;text-align:center;" +
                cursorStyle +
                (selected ? "box-shadow:0 2px 8px rgba(40,167,69,0.3);" : "") +
                '">' +
                '<div style="font-size:18px;font-weight:600;">' +
                displayName +
                "</div>" +
                '<div style="font-size:11px;margin-top:4px;">' +
                statusLabel +
                (capacity ? " &middot; " + capacity : "") +
                "</div>" +
                locationLabel +
                (selected ? '<div style="margin-top:6px;font-size:10px;font-weight:600;color:#28a745;">✓ SELECTED</div>' : "") +
                "</div>";
        }

        html += "</div>";
        return html;
    },

    select_table: function (table_name) {
        var self = this;
        var frm = self.pos_frm;
        if (!frm) {
            frappe.show_alert({
                message: "POS form not ready. Cannot set table.",
                indicator: "red",
            });
            return;
        }

        // Close dialog
        if (self.table_dialog) {
            self.table_dialog.hide();
        }

        // Set table on the invoice
        frm.set_value("canteen_table", table_name);

        // Update table status to Occupied via API
        frappe.call({
            method: "canteen_management.api.update_table_status",
            args: {
                table_name: table_name,
                status: "Occupied",
            },
            callback: function (r) {
                if (r.message && r.message.status === "success") {
                    frappe.show_alert({
                        message: "Table " + table_name + " is now Occupied.",
                        indicator: "blue",
                    });
                }
            },
        });

        // Update toolbar button text
        self._update_table_btn_text(table_name);

        // Also update floating widget table button if present
        var $ftb = $("#canteen-floating-table-btn");
        if ($ftb.length) {
            $ftb.html("🍽️ " + table_name);
        }

        frappe.show_alert({
            message: "Table " + table_name + " assigned.",
            indicator: "green",
        });
    },
};

// Initialize
console.log("[Canteen POS] Script loaded");
canteen_management.pos.init();
