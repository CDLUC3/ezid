document.getElementById('form-shoulder').value = document.querySelectorAll('input[name=selshoulder]')[0].value;

document.querySelectorAll('input[name="selshoulder"]').forEach(radio => {
  radio.addEventListener('change', function () {
    var profile;
    if(this.value.startsWith('ark')) {
      profile = 'erc';
    } else {
      profile = 'datacite';
    }

    const form = document.querySelector('#create_form');
    const formData = new FormData(form);
    formData.set('current_profile', profile);

    // Convert FormData to a query string
    const queryString = new URLSearchParams(formData).toString();
    fetch(`/home/ajax_index_form?${queryString}`, {
        headers: {
            'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value,
        },
    })
    .then(response => response.text())
    .then(data => {
        document.getElementById('form-container').innerHTML = data;  // Replace form container HTML
        document.getElementById('form-shoulder').value = this.value; // needs to happen after the form is replaced
    });
  });
});