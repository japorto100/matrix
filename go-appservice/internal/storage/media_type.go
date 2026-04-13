package storage

import (
	"path/filepath"
	"strings"
)

// ClassifyMediaType derives a MediaType from the given content-type and
// filename. The content-type takes precedence — the filename extension is only
// consulted when the content-type is empty, generic (application/octet-stream),
// or ambiguous.
//
// exec-19 Stufe 3: central classifier used by the Files API listing, so that a
// control-ui filter for type=audio matches both files uploaded with a proper
// audio/mpeg content-type and files uploaded as octet-stream with a .mp3 name.
func ClassifyMediaType(contentType, filename string) MediaType {
	ct := strings.ToLower(strings.TrimSpace(contentType))
	if ct != "" && ct != "application/octet-stream" && ct != "binary/octet-stream" {
		if t := classifyFromContentType(ct); t != MediaTypeOther {
			return t
		}
	}
	if filename != "" {
		if t := classifyFromExtension(filename); t != MediaTypeOther {
			return t
		}
	}
	return MediaTypeOther
}

func classifyFromContentType(ct string) MediaType {
	switch {
	case strings.HasPrefix(ct, "image/"):
		return MediaTypeImage
	case strings.HasPrefix(ct, "audio/"):
		return MediaTypeAudio
	case strings.HasPrefix(ct, "video/"):
		return MediaTypeVideo
	case strings.HasPrefix(ct, "text/"):
		// text/csv → data, text/plain → document, text/html → document.
		// text/tab-separated-values is the official TSV MIME type.
		if strings.Contains(ct, "csv") ||
			strings.Contains(ct, "tsv") ||
			strings.Contains(ct, "tab-separated") {
			return MediaTypeData
		}
		return MediaTypeDocument
	}

	// Specific application/* types
	switch ct {
	case "application/pdf",
		"application/msword",
		"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
		"application/vnd.oasis.opendocument.text",
		"application/rtf":
		return MediaTypeDocument
	case "application/vnd.ms-excel",
		"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		"application/vnd.oasis.opendocument.spreadsheet",
		"application/json",
		"application/x-ndjson",
		"application/x-parquet",
		"application/x-sqlite3":
		return MediaTypeData
	}

	return MediaTypeOther
}

// extensionMap keeps the lookup table outside of classifyFromExtension so it
// allocates once at package init instead of per call.
var extensionMap = map[string]MediaType{
	// documents
	".pdf":  MediaTypeDocument,
	".md":   MediaTypeDocument,
	".mdx":  MediaTypeDocument,
	".txt":  MediaTypeDocument,
	".rtf":  MediaTypeDocument,
	".doc":  MediaTypeDocument,
	".docx": MediaTypeDocument,
	".odt":  MediaTypeDocument,
	".html": MediaTypeDocument,
	".htm":  MediaTypeDocument,
	".epub": MediaTypeDocument,

	// images
	".png":  MediaTypeImage,
	".jpg":  MediaTypeImage,
	".jpeg": MediaTypeImage,
	".gif":  MediaTypeImage,
	".webp": MediaTypeImage,
	".avif": MediaTypeImage,
	".svg":  MediaTypeImage,
	".heic": MediaTypeImage,
	".heif": MediaTypeImage,
	".bmp":  MediaTypeImage,
	".tiff": MediaTypeImage,
	".tif":  MediaTypeImage,

	// audio
	".mp3":  MediaTypeAudio,
	".wav":  MediaTypeAudio,
	".opus": MediaTypeAudio,
	".m4a":  MediaTypeAudio,
	".flac": MediaTypeAudio,
	".ogg":  MediaTypeAudio,
	".oga":  MediaTypeAudio,
	".aac":  MediaTypeAudio,
	".wma":  MediaTypeAudio,

	// video
	".mp4":  MediaTypeVideo,
	".webm": MediaTypeVideo,
	".mkv":  MediaTypeVideo,
	".mov":  MediaTypeVideo,
	".avi":  MediaTypeVideo,
	".m4v":  MediaTypeVideo,
	".mpg":  MediaTypeVideo,
	".mpeg": MediaTypeVideo,

	// data
	".csv":     MediaTypeData,
	".tsv":     MediaTypeData,
	".json":    MediaTypeData,
	".jsonl":   MediaTypeData,
	".ndjson":  MediaTypeData,
	".xlsx":    MediaTypeData,
	".xls":     MediaTypeData,
	".ods":     MediaTypeData,
	".parquet": MediaTypeData,
	".arrow":   MediaTypeData,
	".sqlite":  MediaTypeData,
	".db":      MediaTypeData,
}

func classifyFromExtension(filename string) MediaType {
	ext := strings.ToLower(filepath.Ext(filename))
	if ext == "" {
		return MediaTypeOther
	}
	if t, ok := extensionMap[ext]; ok {
		return t
	}
	return MediaTypeOther
}

// FileExtension returns the lowercase extension without leading dot, or empty.
func FileExtension(filename string) string {
	ext := strings.ToLower(filepath.Ext(filename))
	if ext == "" {
		return ""
	}
	return ext[1:]
}
