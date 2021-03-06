
var btnProcessing_Click = function() {};

// start state: assume not processing until document loaded
var processing = false;

function updateImage() {
    $('.record-img').attr('src', '../api/records/CURRENT/image?time='+new Date().getTime());
}

var processingTimerID = null;

function updateUI_processingStarted() {
    const processing_color = 'red';
    const processing_text = 'Stop';
    var btnStatus = $('#btnStatus a');
    btnStatus.css('background-color', processing_color);
    $('.record-img').css('visibility', 'visible');
    if (processingTimerID !== null) { clearInterval(processingTimerID); }
    processingTimerID = setInterval(updateImage, 1000);
}
function updateUI_processingStopped() {
    const stopped_color = '#00FF00';
    const stopped_text = 'Start';
    var btnStatus = $('#btnStatus a');
    btnStatus.text(stopped_text);
    btnStatus.css('background-color', stopped_color);
    $('.record-img').css('visibility', 'hidden');
    if (processingTimerID !== null) {
        clearInterval(processingTimerID);
        processingTimerID = null;
    }
}
function updateProcessingState(newState) {
    if (typeof(newState) === 'undefined') {
        $.ajax({
            url: '../api/machineState',
            type: 'GET',
            success: function (msg) {
                if (processing != msg.processing) {
                    processing = msg.processing;
                    if (processing == true) { updateUI_processingStarted(); }
                    else { updateUI_processingStopped(); }
                }
            },
            error: function(msg) {
                if (processing != false) {
                    processing = false;
                    stopProcessing();
                }
                console.log(msg);
                alert('ERROR - Could not get machine state.\n'+msg.responseText);
            }
        });
    }
    else {
        if (processing != newState) {
            processing = newState;
            if (processing == true) { updateUI_processingStarted(); }
            else { updateUI_processingStopped(); }
        }
    }
}

$(document).ready(function() {
    updateProcessingState();
    btnProcessing_Click = function() {
        var newState = !processing;
        $.ajax({
            url: '../api/machineState',
            type: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify({ processing: newState }),
            success: function (msg) {
                updateProcessingState(newState);
            },
            error: function(msg) {
                console.log('Error - could not change processing state.\n'+msg);
                updateProcessingState();
            }
        });
    };
});
