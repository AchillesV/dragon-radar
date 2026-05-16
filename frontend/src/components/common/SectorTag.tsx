import { Tag } from 'antd';

interface SectorTagProps {
  text: string;
  color?: string;
}

export default function SectorTag({ text, color = 'default' }: SectorTagProps) {
  return (
    <Tag
      color={color}
      style={{
        fontSize: 11,
        padding: '0 6px',
        lineHeight: '18px',
        borderRadius: 3,
        margin: '2px 2px 2px 0',
      }}
    >
      {text}
    </Tag>
  );
}
