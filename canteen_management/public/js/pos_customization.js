// Canteen Management - POS Customization (v3 - Page toolbar approach)
// Adds employee wallet selector and balance display to ERPNext v15 POS interface.
//
// Strategy:
//   1. Add button to the POS page toolbar via page.add_action_item() — always works,
//      survives Vue re-renders because toolbar is outside the Vue render tree
//   2. Floating widget fallback if page toolbar isn't available
//   3. frappe.ui.form.on for customer change auto-detection

frappe.provide("canteen_management.pos");

canteen_management.pos = {
    employee_dialog: null,
    pos_frm: null,
    _toolbar_btn: null,

    // ========== bootstrap ==========

    init: function () {
        console.log("[Canteen POS] Initializing...");
        var self = this;

        // Register form events (fire in POS because frm.set_value triggers them)
        frappe.ui.form.on("POS Invoice", {
            refresh: function (frm) {
                self.pos_frm = frm;
            },
            customer: function (frm) {
                self.pos_frm = frm;
                self.on_customer_change(frm, frm.doc.customer);
            },
        });

        // Add toolbar button + wait for page to be ready
        this._add_toolbar_button();
    },

    // ========== page toolbar button (PRIMARY) ==========

    _add_toolbar_button: function () {
        var self = this;
        var attempts = 0;

        var try_add = function () {
            attempts++;

            var page = frappe.pages["point-of-sale"];
            if (page && page.add_action_item) {
                console.log("[Canteen POS] Adding toolbar button via page.add_action_item");
                self._toolbar_btn = page.add_action_item(
                    "👤 Canteen Employee — None selected —",
                    function () {
                        self.open_employee_dialog();
                    },
                    { icon: "user" }
                );
                // Add an ID so we can update the text later
                $(self._toolbar_btn).attr("id", "canteen-toolbar-btn");
                return;
            }

            // Try page.page.add_action_item
            if (page && page.page && page.page.add_action_item) {
                console.log("[Canteen POS] Adding toolbar button via page.page.add_action_item");
                self._toolbar_btn = page.page.add_action_item(
                    "👤 Canteen Employee — None selected —",
                    function () {
                        self.open_employee_dialog();
                    },
                    { icon: "user" }
                );
                $(self._toolbar_btn).attr("id", "canteen-toolbar-btn");
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
            '<div id="canteen-pos-floating-widget" style="position:fixed;bottom:80px;right:20px;z-index:1000;">' +
            '    <button class="btn btn-primary btn-sm" id="canteen-floating-btn" style="border-radius:20px;padding:10px 18px;box-shadow:0 4px 12px rgba(0,0,0,0.15);">' +
            '        <span>👤 Select Employee</span>' +
            '        <span id="canteen-floating-badge" style="display:none;margin-left:6px;background:#fff;color:#28a745;border-radius:10px;padding:1px 7px;font-weight:600;">₹0</span>' +
            "    </button>" +
            "</div>";

        $("body").append(html);
        $("#canteen-floating-btn").on("click", function () {
            self.open_employee_dialog();
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
        if (this._toolbar_btn) {
            $(this._toolbar_btn).html(btn_html);
        } else {
            $("#canteen-toolbar-btn").html(btn_html);
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
                    $("#canteen-toolbar-btn").html("👤 " + emp_name + " " + badge_html);

                    // Also update floating badge
                    var $fb = $("#canteen-floating-badge");
                    if ($fb.length) {
                        $fb.text("₹" + bal).show();
                    }
                } else {
                    var badge_html =
                        '<span class="badge" style="background:#dc3545;color:#fff;">No wallet</span>';
                    $("#canteen-toolbar-btn").html("👤 " + emp_name + " " + badge_html);
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
};

// Initialize
console.log("[Canteen POS] Script loaded");
canteen_management.pos.init();
