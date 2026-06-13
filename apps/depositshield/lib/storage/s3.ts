/**
 * S3 helpers for DepositShield property photos.
 * Browser PUTs photos directly via a presigned URL; the report route fetches
 * them server-side and base64-encodes them for the Claude vision call.
 */
import { randomUUID } from "node:crypto";

import { GetObjectCommand, PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

import type { ImageInput } from "../inspection/client";

const BUCKET = process.env.DEPOSITSHIELD_BUCKET ?? "depositshield-uploads";
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

let cachedClient: S3Client | null = null;
function client(): S3Client {
  if (!cachedClient) cachedClient = new S3Client({ region: process.env.AWS_REGION });
  return cachedClient;
}

export function isAllowedImageType(contentType: string): boolean {
  return ALLOWED_TYPES.has(contentType);
}

export async function createUploadUrl(
  contentType: string,
  sessionId: string,
): Promise<{ key: string; url: string }> {
  const ext = contentType.split("/")[1] ?? "jpg";
  const key = `uploads/${sessionId}/${randomUUID()}.${ext}`;
  const url = await getSignedUrl(
    client(),
    new PutObjectCommand({ Bucket: BUCKET, Key: key, ContentType: contentType }),
    { expiresIn: 300 },
  );
  return { key, url };
}

export async function fetchImage(key: string): Promise<ImageInput> {
  const res = await client().send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
  const bytes = await res.Body!.transformToByteArray();
  return {
    mediaType: res.ContentType ?? "image/jpeg",
    base64: Buffer.from(bytes).toString("base64"),
  };
}
