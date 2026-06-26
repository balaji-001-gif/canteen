// Canteen Management - POS Customization
// Handles employee wallet lookup in ERPNext v15 POS interface
// Since POS doesn't render custom fields, this script hooks into customer selection

frappe.provide("canteen_management.pos");

canteen_management.pos = {
    last_checked_customer: null,

    init: function () {
        // Hook into POS Invoice form events (fires in both standard form and POS)
        frappe.ui.form.on("POS Invoice", {
            refresh: function (frm) {
                canteen_management.pos.handle_customer_change(frm);
            },
            customer: function (frm) {
                canteen_management.pos.handle_customer_change(frm);
            },
        });
    },

    handle_customer_change: function (frm) {
        var customer = frm.doc.customer;
        if (!customer || customer === canteen_management.pos.last_checked_customer) {
            return;
        }
        canteen_management.pos.last_checked_customer = customer;

        // Step 1: Find Employee linked to this Customer
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Employee",
                filters: { customer: customer },
                fieldname: ["name", "employee_name"],
            },
            callback: function (r) {
                if (r.message) {
                    var employee = r.message.name;
                    canteen_management.pos.fetch_wallet(frm, employee, r.message.employee_name);
                } else {
                    // No employee linked to this customer - try by customer name
                    frappe.call({
                        method: "frappe.client.get_value",
                        args: {
                            doctype: "Employee",
                            filters: { employee_name: customer },
                            fieldname: ["name", "employee_name"],
                        },
                        callback: function (r2) {
                            if (r2.message) {
                                canteen_management.pos.fetch_wallet(
                                    frm,
                                    r2.message.name,
                                    r2.message.employee_name
                                );
                            }
                        },
                    });
                }
            },
        });
    },

    fetch_wallet: function (frm, employee, employee_name) {
        frappe.call({
            method: "canteen_management.api.get_wallet_balance",
            args: { employee: employee },
            callback: function (r) {
                if (r.message && r.message.balance != null) {
                    // Set fields on the POS Invoice
                    frm.set_value("canteen_employee", employee);
                    frm.set_value("canteen_wallet_balance", r.message.balance);

                    var available =
                        r.message.balance + (r.message.credit_limit || 0);
                    var msg =
                        employee_name +
                        "'s Wallet: ₹" +
                        Number(r.message.balance).toFixed(2);

                    if (r.message.credit_limit > 0) {
                        msg +=
                            " (Credit: ₹" +
                            Number(r.message.credit_limit).toFixed(2) +
                            ")";
                    }

                    frappe.show_alert(
                        {
                            message: msg,
                            indicator:
                                r.message.balance > 0 ? "green" : "orange",
                        },
                        10
                    );
                } else {
                    frappe.show_alert(
                        {
                            message:
                                employee_name +
                                " has no active wallet",
                            indicator: "red",
                        },
                        7
                    );
                }
            },
        });
    },
};

// Initialize on page load
$(document).ready(function () {
    canteen_management.pos.init();
});
