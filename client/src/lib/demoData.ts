import {
    Database,
    Zap,
    ShieldCheck,
    Cpu,
    HardDrive,

    Layers,
    Activity,
    Terminal
} from 'lucide-react';
const archPipeline = [
    {
        id: 1,
        title: 'Document Storage',
        tech: 'Cloudflare R2',
        desc: 'S3-compatible object storage for unformatted enterprise files.',
        icon: HardDrive,
    },
    {
        id: 2,
        title: 'Embeddings',
        tech: 'VoyageAI',
        desc: 'High-density vector models capturing contextual semantic depth.',
        icon: Cpu,
    },
    {
        id: 3,
        title: 'Vector Indexing',
        tech: 'Pinecone & ChromaDB',
        desc: 'Hybrid ANN retrieval with local dynamic storage fallbacks.',
        icon: Database,
    },
    {
        id: 4,
        title: 'Streaming Engine',
        tech: 'FastAPI & SSE',
        desc: 'Asynchronous event pipeline pushing real-time token streams.',
        icon: Zap,
    },
];

const features = [
    {
        icon: Terminal,
        title: 'Real-Time SSE Streaming',
        desc: 'Low-latency token dispatching engineered with FastAPI async generators.',
        metric: '< 120ms',
        metricLabel: 'Time-to-First-Token',
    },
    {
        icon: Layers,
        title: 'Contextual Chunking',
        desc: 'Dynamic chunk boundaries preserving semantic context prior to embedding.',
        metric: '99.4%',
        metricLabel: 'Retrieval Accuracy',
    },
    {
        icon: ShieldCheck,
        title: 'Enterprise JWT Auth',
        desc: 'Role-based access controls paired with session validation routines.',
        metric: 'OAuth 2.0',
        metricLabel: 'Security Spec',
    },
    {
        icon: Activity,
        title: 'Vector Performance',
        desc: 'HNSW indexing delivering sub-50ms query times over production indices.',
        metric: '< 35ms',
        metricLabel: 'Vector Query Latency',
    },
];

const techBadges = [
    'FastAPI',
    'React',
    'LangChain',
    'Cloudflare R2',
    'VoyageAI',
    'Pinecone',
    'ChromaDB',
    'PostgreSQL',
    'TypeScript',
    'Tailwind CSS',
];

export { archPipeline, features, techBadges }