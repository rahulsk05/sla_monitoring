export interface CSVUploadResult {
  accepted_rows: number;
  duplicate_rows: number;
  inserted_rows: number;
  partially_accepted_rows: number;
  rejected_rows: number;
  service_count: number;
  total_source_rows: number;
  upload_id: string;
}

export interface CSVUploadResponse {
  success: boolean;
  data: CSVUploadResult;
}
