import { defineDocs } from "@farming-labs/docs";
import { colorful } from "@farming-labs/theme/colorful";

export default defineDocs({
  entry: "docs",
  theme: colorful(),
  ordering: [
    {
      "slug": "quickstart"
    },
    {
      "slug": "installation"
    },
    {
      "slug": "concepts"
    },
    {
      "slug": "configuration"
    },
    {
      "slug": "scheduler"
    },
    {
      "slug": "cli"
    },
    {
      "slug": "architecture"
    },
    {
      "slug": "roadmap"
    }
  ],
  metadata: {
    titleTemplate: "%s – Docs",
    description: "Managed by @farming-labs/docs Cloud",
  },
});
