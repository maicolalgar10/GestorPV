function __parseMoneyString(value) {
    if (!value) return 0;
    // Remove $, dots, spaces and replace comma with dot
    let raw = value.replace(/\$/g, '').replace(/\./g, '').replace(/,/g, '.').trim();
    let num = parseFloat(raw);
    return isNaN(num) ? 0 : num;
}

function __formatMoneyValue(numberValue) {
    const formatter = new Intl.NumberFormat('es-CO', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
    return "$ " + formatter.format(numberValue);
}

function formatCurrencyField(input) {
    let value = input.value;
    if (!value) return;

    let cleanVal = value.replace(/[^\d\.,\$]/g, "");
    
    // Si termina en coma, permitimos que siga escribiendo
    if (value.endsWith(",")) {
        let num = __parseMoneyString(value);
        input.value = __formatMoneyValue(Math.floor(num)) + ",";
        return;
    } else if (value.endsWith(",0")) {
        let num = __parseMoneyString(value);
        input.value = __formatMoneyValue(Math.floor(num)) + ",0";
        return;
    }

    let num = __parseMoneyString(value);
    if (num !== 0 || value.includes("0")) {
        // preserve the decimal part if it's currently being typed like ,05
        if (value.includes(",") && !value.endsWith(",")) {
            let parts = value.split(",");
            if (parts.length == 2 && parts[1].length > 0) {
                 input.value = __formatMoneyValue(num);
                 return;
            }
        }
        input.value = __formatMoneyValue(num);
    }
}

// Global scope fallbacks for existing oninput attributes
window.formatCurrencyInput = function(input) {
    formatCurrencyField(input);
};
window.formatMoneyField = function(input) {
    formatCurrencyField(input);
};

document.addEventListener("DOMContentLoaded", function() {
    const forms = document.querySelectorAll("form");
    forms.forEach(form => {
        form.addEventListener("submit", function(e) {
            const formCurrencyInputs = form.querySelectorAll(".monto-input, .currency-input");
            formCurrencyInputs.forEach(input => {
                if (input.value) {
                    let num = __parseMoneyString(input.value);
                    // Dejarlo como numero puro para que el backend lo reciba correcto (ej. 1234567.89)
                    input.value = num.toString();
                }
            });
        });
    });
});
