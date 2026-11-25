import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCheckCircle,
  faCloudArrowUp,
  faFileCsv,
  faInfoCircle,
  faTimes,
} from "@fortawesome/free-solid-svg-icons";
import axios from "axios";

import { useCSVUpload } from "../hooks/useCSVUpload";
import type { CSVUploadResult } from "../types/csv-upload.types";

interface CSVUploadModalProps {
  onClose: () => void;
}

const MAX_FILE_SIZE = 5 * 1024 * 1024;

const UPLOAD_SUMMARY_FIELDS: {
  key: keyof Omit<CSVUploadResult, "upload_id">;
  label: string;
}[] = [
  { key: "total_source_rows", label: "Total Source Rows" },
  { key: "inserted_rows", label: "Inserted Rows" },
  { key: "accepted_rows", label: "Accepted Rows" },
  {
    key: "partially_accepted_rows",
    label: "Partially Accepted Rows",
  },
  { key: "duplicate_rows", label: "Duplicate Rows" },
  { key: "rejected_rows", label: "Rejected Rows" },
  { key: "service_count", label: "Service Count" },
];

function validateFile(file: File): string | null {
  if (!file.name.toLowerCase().endsWith(".csv")) {
    return "Only CSV files are supported.";
  }

  if (file.size === 0) {
    return "The selected file is empty.";
  }

  if (file.size > MAX_FILE_SIZE) {
    return "File size must not exceed 5 MB.";
  }

  return null;
}

function getUploadError(error: Error): string {
  if (axios.isAxiosError(error)) {
    const responseData: unknown = error.response?.data;

    if (
      typeof responseData === "object" &&
      responseData !== null &&
      "error" in responseData
    ) {
      const apiError = responseData.error;

      if (
        typeof apiError === "object" &&
        apiError !== null &&
        "message" in apiError &&
        typeof apiError.message === "string"
      ) {
        return apiError.message;
      }
    }

    if (!error.response) {
      return "Unable to connect to the upload service.";
    }
  }

  return "CSV upload failed. Please try again.";
}

export default function CSVUploadModal({ onClose }: CSVUploadModalProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const uploadMutation = useCSVUpload();

  const isUploading = uploadMutation.isPending;
  const uploadResult = uploadMutation.data?.data;

  const handleFileSelection = (file: File) => {
    const error = validateFile(file);

    setValidationError(error);
    uploadMutation.reset();

    setSelectedFile(error ? null : file);
  };

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];

    if (file) {
      handleFileSelection(file);
    }

    event.target.value = "";
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);

    if (isUploading || uploadResult) {
      return;
    }

    const file = event.dataTransfer.files[0];

    if (file) {
      handleFileSelection(file);
    }
  };

  const handleUpload = () => {
    if (!selectedFile || isUploading) {
      return;
    }

    uploadMutation.mutate(selectedFile);
  };

  const handleClose = () => {
    if (!isUploading) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          handleClose();
        }
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="csv-upload-title"
        className="flex w-full max-w-175 flex-col overflow-hidden rounded-xl bg-surface shadow-2xl"
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-border bg-surface-secondary px-6 py-4">
          <div className="flex items-center gap-3">
            <FontAwesomeIcon
              icon={faCloudArrowUp}
              className="text-xl text-primary"
            />

            <h2
              id="csv-upload-title"
              className="text-lg font-semibold text-text-primary"
            >
              Upload CSV
            </h2>
          </div>

          <button
            type="button"
            aria-label="Close upload modal"
            onClick={handleClose}
            disabled={isUploading}
            className="rounded-md p-2 text-text-secondary transition-colors hover:bg-border/50 hover:text-text-primary disabled:opacity-40"
          >
            <FontAwesomeIcon icon={faTimes} />
          </button>
        </div>

        {/* Content */}
        <div className="max-h-[70vh] overflow-y-auto p-6">
          {uploadResult ? (
            <div className="space-y-5">
              <div className="flex flex-col items-center gap-2 text-center">
                <FontAwesomeIcon
                  icon={faCheckCircle}
                  className="text-4xl text-success"
                />

                <h3 className="text-lg font-semibold text-text-primary">
                  CSV Uploaded Successfully
                </h3>

                <p className="text-sm text-text-secondary">
                  Your CSV file has been processed.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {UPLOAD_SUMMARY_FIELDS.map(({ key, label }) => (
                  <div
                    key={key}
                    className="rounded-lg border border-border bg-surface-secondary p-3 text-center"
                  >
                    <p className="text-xl font-semibold text-text-primary">
                      {uploadResult[key].toLocaleString("en-IN")}
                    </p>

                    <p className="mt-1 text-xs text-text-secondary">{label}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div
                onDragOver={(event) => {
                  event.preventDefault();

                  if (!isUploading) {
                    setIsDragging(true);
                  }
                }}
                onDragLeave={(event) => {
                  event.preventDefault();
                  setIsDragging(false);
                }}
                onDrop={handleDrop}
                className={`flex min-h-65 flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
                  isDragging
                    ? "border-primary bg-surface-secondary"
                    : "border-primary/40 bg-surface"
                }`}
              >
                <FontAwesomeIcon
                  icon={faFileCsv}
                  className="mb-4 text-5xl text-primary"
                />

                {selectedFile ? (
                  <>
                    <p className="max-w-full break-all text-sm font-semibold text-text-primary">
                      {selectedFile.name}
                    </p>

                    <p className="mt-2 text-xs text-text-secondary">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-base font-semibold text-text-primary">
                      Drag and drop your CSV file here
                    </p>

                    <p className="my-2 text-sm text-text-secondary">or</p>
                  </>
                )}

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  onChange={handleInputChange}
                  disabled={isUploading}
                />

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                  className="mt-2 rounded-md border border-primary px-5 py-2 text-sm font-medium text-primary transition-colors hover:bg-surface-secondary disabled:opacity-50"
                >
                  <FontAwesomeIcon icon={faCloudArrowUp} className="mr-2" />
                  {selectedFile ? "Change File" : "Choose File"}
                </button>

                <p className="mt-5 text-xs text-text-secondary">
                  <FontAwesomeIcon icon={faInfoCircle} className="mr-2" />
                  Supported format: .csv
                  <span className="mx-2">|</span>
                  Maximum file size: 5 MB
                </p>
              </div>

              {validationError && (
                <p role="alert" className="text-sm text-danger">
                  {validationError}
                </p>
              )}

              {uploadMutation.isError && (
                <p role="alert" className="text-sm text-danger">
                  {getUploadError(uploadMutation.error)}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex shrink-0 justify-end gap-3 border-t border-border px-6 py-4">
          {uploadResult ? (
            <button
              type="button"
              onClick={handleClose}
              className="rounded-md bg-primary px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
            >
              Done
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={handleClose}
                disabled={isUploading}
                className="rounded-md border border-border px-5 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-surface-secondary disabled:opacity-40"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={handleUpload}
                disabled={!selectedFile || isUploading}
                className="rounded-md bg-primary px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isUploading ? "Uploading..." : "Upload"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
