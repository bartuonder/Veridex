export function userIdFromAccessToken(token: string): string {
  const payload = token.split(".")[1];
  if (!payload) {
    return "";
  }
  try {
    const json: unknown = JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
    if (json !== null && typeof json === "object" && "sub" in json && typeof json.sub === "string") {
      return json.sub;
    }
    return "";
  } catch {
    return "";
  }
}
