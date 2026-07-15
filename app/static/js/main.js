document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.password-toggle').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var input = this.parentElement.querySelector('input');
            if (input.type === 'password') {
                input.type = 'text';
                this.querySelector('.eye-open').style.display = 'none';
                this.querySelector('.eye-closed').style.display = '';
            } else {
                input.type = 'password';
                this.querySelector('.eye-open').style.display = '';
                this.querySelector('.eye-closed').style.display = 'none';
            }
        });
    });
});
