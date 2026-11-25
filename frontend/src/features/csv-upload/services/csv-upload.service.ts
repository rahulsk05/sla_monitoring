import { uploadCSV } from "../api/csv-upload.api";
import type { CSVUploadResponse } from "../types/csv-upload.types";

export const csvUploadService = {
  upload: (file: File): Promise<CSVUploadResponse> => uploadCSV(file),
};
