// stops JSLint from complaining
var $;

var estop = function () {
    "use strict";
    var estopElement = $('#estop');
    // TODO: JSLint apparently doesn't like constants...
    const prevText = 'E-stop';
    const prevColor = 'red';
    estopElement.text = '...';
    $.ajax({
        url: '../api/machineState',
        type: 'PUT',
        data: { estopped: true },
        success: function () {
            estopElement.text = 'E-stopped';
            estopElement.css('background-color', '#00FF00');
            setTimeout(function () {
                estopElement.text = prevText;
                estopElement.css('background-color', prevColor);
            }, 500);
        }
    });
};
