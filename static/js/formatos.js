// Check if an input is a money input
function isMoneyInput(el) {
    if (!el || el.tagName !== 'INPUT') return false;
    
    // Check classes
    if (el.classList.contains('monto-input') || el.classList.contains('currency-input')) return true;
    
    // Check name or id keywords
    const keywords = ['monto', 'valor', 'precio', 'costo', 'tarifa', 'saldo'];
    const name = (el.name || '').toLowerCase();
    const id = (el.id || '').toLowerCase();
    
    return keywords.some(k => name.includes(k) || id.includes(k));
}

function formatMoneyWhileTyping(input) {
    let originalValue = input.value;
    if (originalValue === '') return;

    // Get current cursor position
    let cursorPos = input.selectionStart;
    let oldLength = originalValue.length;

    // Remove any character that is not a digit or comma
    // If there is already a comma, we only keep the first one
    let cleanVal = originalValue.replace(/[^\d,]/g, "");
    
    let parts = cleanVal.split(',');
    let integerPart = parts[0];
    let decimalPart = parts.length > 1 ? parts.slice(1).join('') : null;

    // Format integer part with dots
    if (integerPart !== '') {
        integerPart = parseInt(integerPart, 10).toString(); // remove leading zeros
        if (integerPart === 'NaN') integerPart = '0';
        integerPart = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    }

    let formattedValue = integerPart;
    if (decimalPart !== null) {
        // limit decimals to 2 digits
        formattedValue += ',' + decimalPart.substring(0, 2);
    }

    input.value = formattedValue;

    // Adjust cursor position
    let newLength = formattedValue.length;
    let diff = newLength - oldLength;
    let newCursorPos = cursorPos + diff;
    
    // If user deleted a dot, adjust
    if (newCursorPos < 0) newCursorPos = 0;
    
    try {
        input.setSelectionRange(newCursorPos, newCursorPos);
    } catch (e) {
        // Ignore if input type doesn't support selection
    }
}

window.parseMoneda = function(str) {
    if (!str) return 0;
    // Permitir formato DB si es que viene (ej: 1234.56)
    if (/^-?\d+\.\d{1,2}$/.test(String(str).trim())) {
        return parseFloat(String(str).trim());
    }
    // Lógica estricta de Parsing de Moneda
    let partes = str.toString().split(',');
    // Quita puntos y caracteres no numéricos, preservando el signo negativo
    let entero = partes[0].replace(/[^\d-]/g, ''); 
    let decimal = partes.length > 1 ? partes[1].replace(/\D/g, '') : '00';
    return parseFloat(entero + '.' + decimal);
};

function formatMoneyOnBlur(input) {
    let value = String(input.value);
    if (value === '') return;

    let num = window.parseMoneda(value);
    if (isNaN(num)) return;

    // Formatear con Intl para asegurar los 2 decimales y puntos de miles
    const formatter = new Intl.NumberFormat('es-CO', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });

    input.value = formatter.format(num); // Ej: 100.000.000,00
}

function cleanMoneyForSubmit(input) {
    let value = input.value;
    if (!value) return;
    
    let num = window.parseMoneda(value);
    input.value = isNaN(num) ? '' : num.toString();
}

// Global Event Listeners using Event Delegation
document.addEventListener('input', function(e) {
    if (isMoneyInput(e.target)) {
        formatMoneyWhileTyping(e.target);
    }
});

document.addEventListener('blur', function(e) {
    if (isMoneyInput(e.target)) {
        formatMoneyOnBlur(e.target);
    }
}, true); // Use capture for blur

document.addEventListener('submit', function(e) {
    if (e.target.tagName === 'FORM') {
        const inputs = e.target.querySelectorAll('input[type="text"], input[type="number"]');
        inputs.forEach(input => {
            if (isMoneyInput(input)) {
                cleanMoneyForSubmit(input);
            }
        });
    }
});

// Polyfills for existing inline handlers to prevent errors
window.formatCurrencyInput = function(input) {
    // We can just call formatMoneyWhileTyping or let the event listener handle it
    formatMoneyWhileTyping(input);
};
window.formatMoneyField = function(input) {
    formatMoneyWhileTyping(input);
};

// Also format any pre-filled money inputs on page load
document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('input');
    inputs.forEach(input => {
        if (isMoneyInput(input) && input.value && input.value !== '0') {
            formatMoneyOnBlur(input);
        }
    });
});
