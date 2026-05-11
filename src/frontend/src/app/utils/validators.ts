import { ParameterUI } from '../models/ui/forms.ui'; // Import your UI model

export class ValidatorsUtil {

  static isNumericType(type: string): boolean {
    if (!type) return false;
    const t = type.toLowerCase();
    return ['number', 'integer', 'float', 'int'].includes(t);
  }

  /**
   * Validates a parameter and updates its error state directly.
   * Returns true if valid, false otherwise.
   */
  static validateParameter(param: ParameterUI, showError: boolean = false): boolean {
    // Reset error state
    if (!showError) {
      param.hasError = false;
      param.errorMessage = '';
    }

    let isValid = true;
    let errorMessage = '';

    // 1. Required Check
    if (param.required && (param.value === undefined || param.value === null || param.value === '')) {
      isValid = false;
      errorMessage = 'This field is required.';
    }
    // 2. Numeric Checks
    else if (this.isNumericType(param.type)) {
      const numValue = Number(param.value);

      if (param.value === '' || isNaN(numValue)) {
        isValid = false;
        errorMessage = 'Please enter a valid number.';
      } else {
        // ✅ FIX: Use '!= null' to check for both null and undefined
        if (param.min != null && numValue < param.min) {
          isValid = false;
          errorMessage = `Value must be at least ${param.min}.`;
        } 
        // ✅ FIX: Same here
        else if (param.max != null && numValue > param.max) {
          isValid = false;
          errorMessage = `Value cannot exceed ${param.max}.`;
        }
      }
    }
    // 3. Options Check
    else if (param.options && param.options.length > 0) {
      // Ensure strict string matching
      if (!param.options.includes(String(param.value))) {
        isValid = false;
        errorMessage = `Please select from: ${param.options.join(', ')}.`;
      }
    }

    if (showError) {
      param.hasError = !isValid;
      param.errorMessage = errorMessage;
    }

    return isValid;
  }
}