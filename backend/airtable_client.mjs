import Airtable from "airtable";
import dns from "node:dns";
import https from "node:https";

// In some Docker network environments, Node can repeatedly choose an
// unreachable address from Airtable's multi-address DNS response. The client
// process only talks to Airtable, so choose one IPv4 address at random per
// request and let the Python adapter retry a failed connection.
https.globalAgent.options.lookup = (hostname, options, callback) => {
  dns.resolve4(hostname, (error, addresses) => {
    if (error) {
      callback(error);
      return;
    }
    const address = addresses[Math.floor(Math.random() * addresses.length)];
    if (options.all) {
      callback(null, [{ address, family: 4 }]);
      return;
    }
    callback(null, address, 4);
  });
};

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
