/**
 * S3 helpers for GradeLens device photos.
 *
 * Upload path: the browser asks /api/upload-url for a presigned PUT, then PUTs
 * the photo directly to S3 (keeps large image bytes off the serverless function).
 * Grade path: /api/grade fetches the objects server-side and base64-encodes them
 * for the Claude vision call.
 */
import { randomUUID } from "node:crypto";

import { GetObjectCommand, PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

import type { ImageInput } from "../grading/client";

const BUCKET = process.env.GRADELENS_BUCKET ?? "gradelens-uploads";
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

let cachedClient: S3Client | null = null;
function client(): S3Client {
  if (!cachedClient) cachedClient = new S3Client({ region: process.env.AWS_REGION });
  return cachedClient;
}

export function isAllowedImageType(contentType: string): boolean {
  return ALLOWED_TYPES.has(contentType);
}

/** Create a presigned PUT URL plus the object key the client should report back. */
export async function createUploadUrl(
  contentType: string,
): Promise<{ key: string; url: string }> {
  const ext = contentType.split("/")[1] ?? "jpg";
  const key = `uploads/${new Date().toISOString().slice(0, 10)}/${randomUUID()}.${ext}`;
  const url = await getSignedUrl(
    client(),
    new PutObjectCommand({ Bucket: BUCKET, Key: key, ContentType: contentType }),
    { expiresIn: 300 },
  );
  return { key, url };
}

/** Fetch an uploaded object and return it as a base64 ImageInput for the model. */
export async function fetchImage(key: string): Promise<ImageInput> {
  const res = await client().send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
  const bytes = await res.Body!.transformToByteArray();
  return {
    mediaType: res.ContentType ?? "image/jpeg",
    base64: Buffer.from(bytes).toString("base64"),
  };
}
