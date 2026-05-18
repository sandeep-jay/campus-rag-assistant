import { SharedArray } from "k6/data";
const u = new SharedArray("x", () => JSON.parse(open("./users.json")));
export default function () {}
