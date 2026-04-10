/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  basePath: '/trading',
  trailingSlash: true,
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
