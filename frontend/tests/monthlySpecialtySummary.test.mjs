import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { buildMonthlySpecialtySummary } from "../src/features/reporting/monthlySpecialtySummary.js";

test("cierre mensual separa OT únicas del mes y OT únicas programadas", () => {
  const summary = buildMonthlySpecialtySummary({
    specialties: [{
      especialidad: "ELE", programmed: 646, finalized: 298, progress_ot_pct: 46.1,
    }],
    monthly_progress_by_specialty: [{
      especialidad: "ELE", name: "Eléctrica", total_ot: 479, completed_ot: 410,
      progress_ot_pct: 85.6, scheduled_completed: 298, unplanned_completed: 112,
      scheduled_unique: 357, scheduled_assignments: 646,
      scheduled_reprogrammed_assignments: 289, scheduled_progress_ot_pct: 83.5,
    }],
  }, { ELE: "Eléctrica" });

  assert.equal(summary.length, 1);
  assert.equal(summary[0].name, "Eléctrica");
  assert.equal(summary[0].monthly.progress_ot_pct, 85.6);
  assert.equal(summary[0].monthly.completed_ot, 410);
  assert.equal(summary[0].monthly.total_ot, 479);
  assert.equal(summary[0].weekly.progress_ot_pct, 46.1);
  assert.equal(summary[0].weekly.programmed, 646);
  assert.equal(summary[0].weekly.finalized, 298);
  assert.equal(summary[0].monthly.scheduled_unique, 357);
  assert.equal(summary[0].monthly.scheduled_completed, 298);
  assert.equal(summary[0].monthly.scheduled_progress_ot_pct, 83.5);
  assert.equal(summary[0].monthly.scheduled_reprogrammed_assignments, 289);
});

test("incluye especialidad con cartera mensual aunque no tenga programación semanal", () => {
  const summary = buildMonthlySpecialtySummary({
    specialties: [],
    monthly_progress_by_specialty: [{
      especialidad: "SER", total_ot: 10, completed_ot: 2, progress_ot_pct: 20,
    }, { especialidad: "MET", total_ot: 0, completed_ot: 0, progress_ot_pct: 0 }],
  });
  assert.deepEqual(summary.map((row) => row.especialidad), ["SER"]);
  assert.equal(summary[0].weekly, null);
});

test("las especialidades sin dato mensual no muestran el porcentaje semanal como mensual", () => {
  const summary = buildMonthlySpecialtySummary({
    specialties: [{ especialidad: "MEC", progress_ot_pct: 60 }],
  });
  assert.equal(summary[0].monthly, null);
  assert.equal(summary[0].weekly.progress_ot_pct, 60);
});

test("la vista consolidada no confunde 646 asignaciones con OT programadas diferentes", () => {
  const source = readFileSync(new URL("../src/components/MonthlyClose.jsx", import.meta.url), "utf8");
  const dashboard = readFileSync(new URL("../src/components/ProgressDashboard.jsx", import.meta.url), "utf8");
  assert.ok(source.includes("row.monthly.progress_ot_pct"));
  assert.ok(source.includes("row.monthly.scheduled_progress_ot_pct"));
  assert.ok(source.includes("row.monthly.scheduled_unique"));
  assert.ok(source.includes("row.monthly.scheduled_reprogrammed_assignments"));
  assert.ok(!source.includes("row.weekly.progress_ot_pct"));
  assert.ok(!source.includes("row.weekly.programmed"));
  assert.ok(source.includes("row.monthly.completed_ot"));
  assert.ok(source.includes("row.monthly.unplanned_completed"));
  assert.ok(dashboard.includes("row.progress_ot_pct"));
  assert.ok(dashboard.includes("monthlyProgressBySpecialty.map"));
});
