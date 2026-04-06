package base

import "testing"

func TestParseSeriesTime(t *testing.T) {
	tests := []struct {
		name   string
		format string
		value  string
		want   string
		ok     bool
	}{
		{name: "iso", format: DateFormatISODate, value: "2026-02-23", want: "2026-02-23", ok: true},
		{name: "slash-dmy", format: DateFormatSlashDMY, value: "23/02/2026", want: "2026-02-23", ok: true},
		{name: "yyyymm", format: DateFormatYYYYMM, value: "202602", want: "2026-02-01", ok: true},
		{name: "yyyy", format: DateFormatYYYY, value: "2026", want: "2026-01-01", ok: true},
		{name: "quarter", format: DateFormatQuarterCode, value: "2026Q3", want: "2026-07-01", ok: true},
		{name: "bad-quarter", format: DateFormatQuarterCode, value: "2026Q9", ok: false},
		{name: "unsupported", format: "custom", value: "2026", ok: false},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := ParseSeriesTime(tc.format, tc.value)
			if (err == nil) != tc.ok {
				t.Fatalf("ParseSeriesTime(%q,%q) err=%v ok=%v", tc.format, tc.value, err, tc.ok)
			}
			if !tc.ok {
				return
			}
			if got.Format("2006-01-02") != tc.want {
				t.Fatalf("expected %s, got %s", tc.want, got.Format("2006-01-02"))
			}
		})
	}
}
