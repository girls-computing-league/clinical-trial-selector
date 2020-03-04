var socket = io();

$("a[href=\"/getInfo\"]").click(openSocket)

function openSocket() {
    document.getElementById("progress").style.display = "block";
    socket.on('update_progress', function(message) {
        $('.progress-bar-inner').css('width', message.data+'%')
                                .attr('aria-valuenow', message.data);
        $('.progress-bar-label').text(message.data+'%');
    });
};

socket.on('disconnect', function(message) {
    socket.disconnect()
});
