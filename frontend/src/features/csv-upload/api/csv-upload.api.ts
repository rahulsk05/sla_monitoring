import { uploadApi } from "../../../lib/axios";
import type { CSVUploadResponse } from "../types/csv-upload.types";

export async function uploadCSV(file: File): Promise<CSVUploadResponse> {
  const formData = new FormData();

  formData.append("file", file);

  const response = await uploadApi.post<CSVUploadResponse>("/", formData);

  return response.data;
}
