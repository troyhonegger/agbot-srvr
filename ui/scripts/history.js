
$(document).ready(function() {
    $.ajax({
        url: '../api/records',
        type: 'GET',
        success: function (msg) {
            if (msg.length !== 0) {
                var historyTable = $('#history_table');
                for (var i = 0; i < msg.length; i++) {
                    historyTable.append('<tr><td><a href="record.html?recordID='+msg[i].recordID+'">'+msg[i].name+'</a></td></tr>');
                }
                historyTable.css('visibility', 'visible');
                $('#history_notfound').css('visibility', 'collapse');
            }
        },
        error: function (msg) {
            // log the error message, but don't do anything else; just leave the default "no records found" content
            console.log(msg);
        }
    });
});
