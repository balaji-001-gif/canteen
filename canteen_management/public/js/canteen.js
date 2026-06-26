// Canteen Management - Global JS helpers

frappe.provide("canteen_management");

canteen_management.utils = {
    format_money: function (amount) {
        return "₹" + frappe.utils.flt(amount, 2).toFixed(2);
    },

    show_success: function (msg) {
        frappe.show_alert({ message: msg, indicator: "green" }, 5);
    },

    show_error: function (msg) {
        frappe.show_alert({ message: msg, indicator: "red" }, 7);
    },
};

// POS Invoice: auto-fetch wallet balance when employee is selected
frappe.ui.form.on("POS Invoice", {
    refresh: function (frm) {
        // Populate balance when form loads with an existing employee
        if (frm.doc.canteen_employee) {
            canteen_management.utils.update_wallet_balance(frm, frm.doc.canteen_employee);
        }
    },

    canteen_employee: function (frm) {
        canteen_management.utils.update_wallet_balance(frm, frm.doc.canteen_employee);
    },
});

canteen_management.utils.update_wallet_balance = function (frm, employee) {
    if (employee) {
        frappe.call({
            method: "canteen_management.api.get_wallet_balance",
            args: { employee: employee },
            callback: function (r) {
                if (r.message && r.message.balance != null) {
                    frm.set_value("canteen_wallet_balance", r.message.balance);
                } else {
                    frm.set_value("canteen_wallet_balance", 0);
                }
            },
        });
    } else {
        frm.set_value("canteen_wallet_balance", 0);
    }
};
