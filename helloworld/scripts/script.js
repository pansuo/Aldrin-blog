// script.js for blogbase.html

$(document).ready(function() {
	$('.location').click(function() {
		$(this).nextAll('img').toggle(300);
	});

	$('.places_picture').fadeIn(1000);
	$('.post').fadeIn(500);
	$('.newpostform').fadeIn(500);
	$('.aboutmepage').fadeIn(500);

});

