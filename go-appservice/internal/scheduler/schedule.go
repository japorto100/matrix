package scheduler

import (
	"fmt"

	"github.com/riverqueue/river"
	"github.com/robfig/cron/v3"
)

// parseStandardSchedule wraps robfig/cron's standard parser so our
// infra-task cron strings ("* * * * *", "0 3 * * 1") produce a value
// River accepts as river.PeriodicSchedule.
func parseStandardSchedule(expr string) (river.PeriodicSchedule, error) {
	schedule, err := cron.ParseStandard(expr)
	if err != nil {
		return nil, fmt.Errorf("parse cron %q: %w", expr, err)
	}
	return schedule, nil
}
