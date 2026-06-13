/** @type {import('next').NextConfig} */
const nextConfig = {
  // Route Handlers do the AWS + Anthropic work server-side; nothing to expose.
  experimental: {
    // Allow larger request bodies on the grade route (base64 image fallback path).
    serverActions: { bodySizeLimit: "12mb" },
  },
};

export default nextConfig;
