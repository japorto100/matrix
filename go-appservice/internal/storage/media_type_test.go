package storage

import "testing"

func TestClassifyMediaType(t *testing.T) {
	cases := []struct {
		name        string
		contentType string
		filename    string
		want        MediaType
	}{
		// Content-type wins when specific
		{"pdf by mime", "application/pdf", "foo.bin", MediaTypeDocument},
		{"png by mime", "image/png", "", MediaTypeImage},
		{"jpg by mime uppercase", "IMAGE/JPEG", "", MediaTypeImage},
		{"mp3 by mime", "audio/mpeg", "", MediaTypeAudio},
		{"mp4 by mime", "video/mp4", "", MediaTypeVideo},
		{"csv by mime", "text/csv", "", MediaTypeData},
		{"tsv by mime", "text/tab-separated-values", "", MediaTypeData},
		{"text plain → document", "text/plain", "", MediaTypeDocument},
		{"text html → document", "text/html", "", MediaTypeDocument},
		{"json by mime", "application/json", "", MediaTypeData},
		{"ndjson by mime", "application/x-ndjson", "", MediaTypeData},
		{"xlsx by mime", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "", MediaTypeData},
		{"docx by mime", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "", MediaTypeDocument},

		// Fallback to extension when octet-stream or empty
		{"octet stream falls back to ext", "application/octet-stream", "report.pdf", MediaTypeDocument},
		{"empty ct uses ext", "", "song.mp3", MediaTypeAudio},
		{"empty ct uses ext 2", "", "clip.webm", MediaTypeVideo},
		{"empty ct uses ext 3", "", "data.parquet", MediaTypeData},

		// Extension variants
		{"opus audio ext", "", "voice.opus", MediaTypeAudio},
		{"heic image ext", "", "IMG_0123.HEIC", MediaTypeImage},
		{"mkv video ext", "", "movie.mkv", MediaTypeVideo},
		{"odt document ext", "", "note.odt", MediaTypeDocument},
		{"sqlite data ext", "", "store.sqlite", MediaTypeData},

		// Unknown → other
		{"unknown both", "application/x-foobar", "thing.xyz", MediaTypeOther},
		{"empty both", "", "", MediaTypeOther},
		{"unknown ext only", "", "file.quux", MediaTypeOther},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := ClassifyMediaType(tc.contentType, tc.filename)
			if got != tc.want {
				t.Errorf("ClassifyMediaType(%q, %q) = %q, want %q",
					tc.contentType, tc.filename, got, tc.want)
			}
		})
	}
}

func TestFileExtension(t *testing.T) {
	cases := map[string]string{
		"report.pdf":   "pdf",
		"IMG.JPEG":     "jpeg",
		"no_ext":       "",
		"multi.dot.md": "md",
		".hidden":      "hidden", // leading dot: treated as extension by filepath.Ext
		"":             "",
	}
	for in, want := range cases {
		if got := FileExtension(in); got != want {
			t.Errorf("FileExtension(%q) = %q, want %q", in, got, want)
		}
	}
}
