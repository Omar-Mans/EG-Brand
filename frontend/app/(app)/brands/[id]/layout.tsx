import BrandFrame from "@/components/BrandFrame";

export default function BrandLayout({ children }: { children: React.ReactNode }) {
  return <BrandFrame>{children}</BrandFrame>;
}
