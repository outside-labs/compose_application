import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';

const {runSourceRequest} = await import(pathToFileURL(resolve(process.argv[2], 'runtime/source-request.mjs')));
let raw = '';
for await (const chunk of process.stdin) {
  raw += chunk;
  if (raw.length > 1048576) throw new Error('Probe input exceeds 1 MiB.');
}
const results = [];
for (const probe of JSON.parse(raw)) {
  const result = await runSourceRequest({
    modules: [{name: 'app', source: probe.source, package: false, imports: probe.imports,
               notice: 'Synthetic composition prerequisite probe'}],
    compileOptions: {languageProfile: 'classes-source/1'},
    options: {maxSteps: 100000, maxWork: 1000000},
  });
  const closed = result.closed;
  if (closed && ['bytes', 'objects', 'roots', 'frames'].some(key => closed[key] !== 0)) {
    throw new Error(`Probe retained logical resources: ${probe.id}`);
  }
  if (!result.ok && !['UNSUPPORTED', 'IMPORT'].includes(result.error.code) && result.error.type !== 'ImportError') {
    throw new Error(`Unexpected probe failure: ${probe.id}: ${JSON.stringify(result.error)}`);
  }
  results.push({id: probe.id, status: result.ok ? 'supported' : 'refused', stdout: result.stdout,
                error: result.error || null, closed: closed || null});
}
process.stdout.write(JSON.stringify({node: process.version, language_profile: 'classes-source/1', results}));
