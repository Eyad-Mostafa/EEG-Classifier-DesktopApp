export class FileUtils {
  static isValidExtension(file: File, allowedTypes: string[]): boolean {
    const ext = file.name.split('.').pop()?.toLowerCase();
    const cleanAllowed = allowedTypes.map(t => t.replace('.', '').toLowerCase());
    return !!ext && cleanAllowed.includes(ext);
  }

  static getFileSize(file: File): string {
    return (file.size / 1024 / 1024).toFixed(2) + ' MB';
  }
}