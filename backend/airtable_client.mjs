import Airtable from "airtable";

const input = await new Promise((resolve, reject) => {
  let body = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => { body += chunk; });
  process.stdin.on("end", () => resolve(JSON.parse(body)));
  process.stdin.on("error", reject);
});

const table = new Airtable({ apiKey: input.apiKey }).base(input.baseId)(input.tableName);
const fields = input.fields;

try {
  const record = input.recordId
    ? await table.update(input.recordId, fields, { typecast: true })
    : await table.create(fields, { typecast: true });
  process.stdout.write(JSON.stringify({ id: record.id }));
} catch (error) {
  process.stderr.write(JSON.stringify({ message: error.message, statusCode: error.statusCode }));
  process.exitCode = 1;
}
