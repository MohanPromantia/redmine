// // Copyright (c) 2024, Mohan and contributors

frappe.ui.form.on('Redmine Timesheet', {
    refresh(frm) {
        frm.add_custom_button(__('Upload to Insights'), function() {
            // Show the progress bar before calling the server method
            frappe.show_progress('Loading..', 10, 100, 'Uploading to Insights');
            
            frm.call('upload_to_insights').then(() => {
               
                frappe.hide_progress();
            });
        });
    }
});

// Listen for the show_progress and hide_progress events
frappe.realtime.on("show_progress", function(data) {
    frappe.show_progress(data.message, data.percent, 100, 'Please wait');
});

frappe.realtime.on("hide_progress", function(data) {
    frappe.hide_progress();
});

