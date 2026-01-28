'use client';

import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Sparkles, Loader2, Copy, CheckCircle } from 'lucide-react';
import apiClient from '@/lib/api-client';

interface SaasIdea {
  id: string;
  name: string;
  description: string;
  targetAudience: string;
  monetization: string;
  techStack: string[];
}

export default function AIIdeasPage() {
  const [prompt, setPrompt] = useState('');
  const [ideas, setIdeas] = useState<SaasIdea[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const generateIdeas = async () => {
    if (!prompt.trim()) return;
    setIsLoading(true);
    setError('');
    try {
      // Split prompt into keywords for the backend
      const keywords = prompt.split(',').map(k => k.trim()).filter(k => k.length > 0);
      const response = await apiClient.post('/integrations/openai/generate-ideas/', { keywords });

      // Backend returns { ideas: { ideas: [...] } } or similar structure depending on Pydantic model
      // We need to adapt the response to our frontend state
      const ideasData = response.data.ideas.ideas || response.data.ideas || [];

      // Map backend response to frontend interface if needed
      // Assuming backend returns a compatible structure, otherwise we'd need a mapper
      setIdeas(ideasData);
    } catch (err) {
      setError('Failed to generate ideas. Please try again.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };


  const copyToClipboard = (idea: SaasIdea) => {
    navigator.clipboard.writeText(`${idea.name} - ${idea.description}`);
    setCopiedId(idea.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">AI SaaS Ideas Generator</h1>
        <p className="text-gray-500">Generate innovative SaaS business ideas powered by AI</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            Generate Ideas
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4">
            <Input
              placeholder="Enter keywords separated by commas (e.g., healthcare, ai, remote work)"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="flex-1"
            />
            <Button onClick={generateIdeas} disabled={isLoading || !prompt.trim()}>
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Generate
                </>
              )}
            </Button>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </CardContent>
      </Card>

      {ideas.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {ideas.map((idea) => (
            <Card key={idea.id}>
              <CardHeader>
                <CardTitle className="text-lg">{idea.name}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-gray-600">{idea.description}</p>
                <div>
                  <p className="text-xs font-medium text-gray-500">Target Audience</p>
                  <p className="text-sm">{idea.targetAudience}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Monetization</p>
                  <p className="text-sm">{idea.monetization}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Tech Stack</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {idea.techStack.map((tech) => (
                      <span key={tech} className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">
                        {tech}
                      </span>
                    ))}
                  </div>
                </div>
              </CardContent>
              <CardFooter>
                <Button variant="outline" size="sm" onClick={() => copyToClipboard(idea)} className="w-full">
                  {copiedId === idea.id ? (
                    <>
                      <CheckCircle className="mr-2 h-4 w-4 text-green-500" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="mr-2 h-4 w-4" />
                      Copy Idea
                    </>
                  )}
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
