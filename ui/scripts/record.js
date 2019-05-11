function getRecordID() {
    if (window.location.search.length > 0) {
        var params = window.location.search.substring(1).split('&');
        for (var i = 0; i < params.length; i++) {
            if (params[i].startsWith('recordID=')) {
                return params[i].substring(9);
            }
        }
    }
    return null;
}

function hideRecordInfo() {
    $('.record-img').css('visibility', 'collapse');
    $('#record_notfound').css('visibility', 'visible');
}

function dateFormat(dateStr) {
    date = new Date(dateStr);
    var hrs = date.getHours();
    var min = date.getMinutes();
    var am = hrs < 12;
    hrs = hrs % 12;
    if (hrs === 0) { hrs = 12; }
    min = min.toString();
    if (min.length == 1) { min = '0' + min; }
    return date.toDateString() + ', ' + hrs + ':' + min + (am ? ' AM' : ' PM');
}

function updateRecordSummary(recordID) {
    $.ajax({
        url: '../api/records/'+recordID,
        type: 'GET',
        success: function (msg) {
            var div = $('#record_info');
            div.append('<h1>'+msg.name+'</h1>');
            div.append('<hr>');
            div.append('<p><span class="header">Start Time: </span>'+dateFormat(msg.startTime)+'</p>');
            div.append('<p><span class="header">End Time: </span>'+dateFormat(msg.endTime)+'</p>');
            div.append('<p><span class="header">Latitude: </span>'+msg.latitude+'</p>');
            div.append('<p><span class="header">Longitude: </span>'+msg.longitude+'</p>');
            div.css('visibility', 'visible');
            $('#record_notfound').css('visibility', 'collapse');
        },
        error: function (msg) {
            // log the error message, but don't do anything else; just leave the default "no records found" content
            console.log('Error getting record summary: '+JSON.stringify(msg));
            hideRecordInfo();
        }
    });
}

$(document).ready(function (){
    var recordID = getRecordID();
    if (recordID !== null) {
        $('#record_info').after('<img class="record-img" src="api/records/'+recordID+'/image"></img>')
        updateRecordSummary(recordID);
    }
});