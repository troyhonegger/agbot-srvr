$(document).ready(function() {
    $.ajax({
        url: '../api/cameras',
        type: 'GET',
        success: function (msg) {
            if (msg.length !== 0) {
                var camerasTable = $('#cameras_table');
                for (var i = 0; i < msg.length; i++) {
                    camerasTable.append('<tr><td><a href="livefeed.html?cameraID='+msg[i].cameraID+'">'+msg[i].name+'</a></td></tr>');
                }
                camerasTable.css('visibility', 'visible');
                $('#cameras_notfound').css('visibility', 'collapse');
            }
        },
        error: function (msg) {
            // log the error message, but don't do anything else; just leave the default "no cameras found" content
            console.log(msg);
        }
    });
});
