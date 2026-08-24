import { FileUp, LoaderCircle } from "lucide-react";
import { useState, type DragEvent } from "react";

export function ResumeUpload({
  disabled,
  onFile,
  selectedFileName,
}: {
  disabled: boolean;
  onFile: (file: File | undefined) => void;
  selectedFileName?: string;
}) {
  const [dragging, setDragging] = useState(false);
  const selectFile = (file: File | undefined) => {
    setDragging(false);
    onFile(file);
  };
  const handleDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    selectFile(event.dataTransfer.files[0]);
  };
  return (
    <label
      className={`profile-upload ${dragging ? "profile-upload-dragging" : ""} ${disabled ? "profile-upload-disabled" : ""}`}
      onDragEnter={() => setDragging(true)}
      onDragLeave={() => setDragging(false)}
      onDragOver={(event) => event.preventDefault()}
      onDrop={handleDrop}
    >
      <span className="profile-upload-icon">
        {disabled ? (
          <LoaderCircle className="ui-spinner" size={22} aria-hidden="true" />
        ) : (
          <FileUp size={22} aria-hidden="true" />
        )}
      </span>
      <span className="profile-upload-title">
        {disabled
          ? "Analyzing your resume..."
          : selectedFileName
            ? "Replace your resume"
            : "Upload your resume"}
      </span>
      <span className="profile-upload-help">
        Drag and drop a file here, or click to browse. PDF only, up to 10 MB.
      </span>
      {selectedFileName && !disabled && (
        <span className="profile-upload-selected">Selected: {selectedFileName}</span>
      )}
      <input
        accept="application/pdf,.pdf"
        disabled={disabled}
        type="file"
        onChange={(event) => selectFile(event.target.files?.[0])}
      />
    </label>
  );
}
