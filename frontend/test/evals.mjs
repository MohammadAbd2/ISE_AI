import assert from "node:assert/strict";
import { classifyTaskIntent } from "../src/lib/taskIntent.js";
import { buildVisualizationArtifacts, buildVisualizationSpec } from "../src/lib/visualization.js";

const chartIntent = classifyTaskIntent("create a 2d chart with random 1 year salary", "auto");
assert.equal(chartIntent.kind, "visualization");
assert.equal(chartIntent.useAgent, false);

const codeIntent = classifyTaskIntent("create file frontend/src/components/Hello.jsx", "auto");
assert.equal(codeIntent.kind, "coding");
assert.equal(codeIntent.useAgent, true);

const chartSpec = buildVisualizationSpec(`display this salary data in a 2d diagram
jan 10000 dkk
feb 12000 dkk
mar 7000 dkk
apr 15000 dkk
maj 3500 dkk`);
assert.equal(chartSpec.type, "chart2d");
assert.equal(chartSpec.rows.length, 5);

const randomYearSpec = buildVisualizationSpec("create a 2d chart with random 1 year salary");
assert.equal(randomYearSpec.type, "chart2d");
assert.equal(randomYearSpec.rows.length, 12);
const randomYearArtifacts = buildVisualizationArtifacts(randomYearSpec);
assert.equal(randomYearArtifacts[0].type, "report");
assert.equal(randomYearArtifacts[1].type, "file_result");

const mapSpec = buildVisualizationSpec(`show me a 3d map
FlightA,55.67,12.56,32000
FlightB,40.71,-74.0,28000`);
assert.equal(mapSpec.type, "map3d");
assert.equal(mapSpec.points.length, 2);
const mapArtifacts = buildVisualizationArtifacts(mapSpec);
assert.equal(mapArtifacts[0].type, "report");
assert.equal(mapArtifacts[1].type, "file_result");

console.log("frontend evals passed");
