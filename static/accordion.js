$(document).ready(function () {
    $(".tbtn").click(function () {
        $(this).parents("tbody").find(".toggler").addClass("togglerTemp").removeClass("toggler");
        $(this).parents("tbody").find(".fa-plus-circle").addClass("fa-Temp").removeClass("fa-plus-circle");
        $(this).parents("tbody").find(".toggler1").addClass("toggler").removeClass("toggler1");
        $(this).parents("tbody").find(".fa-minus-circle").addClass("fa-plus-circle").removeClass("fa-minus-circle");
        $(this).parents("tbody").find(".togglerTemp").addClass("toggler1").removeClass("togglerTemp");
        $(this).parents("tbody").find(".fa-Temp").addClass("fa-minus-circle").removeClass("fa-Temp");
    });
});

/*
$(document).ready(function () {
    $(".tbtn").click(function () {
       $(this).parents(".custom-table").find(".toggler1").removeClass("toggler1");
        $(this).parents("tbody").find(".toggler").addClass("toggler1");
        $(this).parents(".custom-table").find(".fa-minus-circle").removeClass("fa-minus-circle");
        $(this).parents("tbody").find(".fa-plus-circle").addClass("fa-minus-circle");
    });
});
*/