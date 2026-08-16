export const MIN_PASSWORD_LENGTH = 12;

export type CredentialErrors = {
  email?: string;
  password?: string;
};

export function validateEmail(email: string): string | undefined {
  return /^\S+@\S+\.\S+$/.test(email.trim()) ? undefined : "Enter a valid email address.";
}

export function validateCredentials(email: string, password: string): CredentialErrors {
  const errors: CredentialErrors = {};
  const emailError = validateEmail(email);
  if (emailError) {
    errors.email = emailError;
  }
  if (password.length < MIN_PASSWORD_LENGTH) {
    errors.password = `Use at least ${MIN_PASSWORD_LENGTH} characters. A memorable passphrase works well.`;
  }
  return errors;
}
