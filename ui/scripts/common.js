
function estop() {
    "use strict";
    var estopElement = $('#estop');
    // TODO: JSLint apparently doesn't like constants...
    const prevText = 'E-stop';
    const prevColor = 'red';
    estopElement.text('...');
    $.ajax({
        url: '../api/machineState',
        type: 'PUT',
        contentType: 'application/json',
        data: JSON.stringify({ estopped: true }),
        success: function (msg) {
            estopElement.text('E-stopped');
            estopElement.css('background-color', '#00FF00');
            setTimeout(function () {
                estopElement.text(prevText);
                estopElement.css('background-color', prevColor);
            }, 500);
        },
        error: function(msg) {
            estopElement.text(prevText);
            estopElement.css('background-color', prevColor);
            console.log(msg);
            alert('ERROR - Estop FAILED\n'+msg.responseText);
        }
    });
};
