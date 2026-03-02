/**
 * NWChem Input File Parser
 * 
 * Parses NWChem quantum chemistry input files (.nw)
 * including geometry, basis, scf blocks, and task directives.
 */

export interface ParseContext {
  lineNumber: number;
  column: number;
  currentSection: string | null;
  sectionStack: string[];
  lineContent: string;
  wordAtCursor: string;
  isInBlock: boolean;
}

export interface NWChemSection {
  name: string;
  startLine: number;
  endLine: number | null;
  keywords: string[];
  content: string[];
}

export interface GeometryBlock {
  units: string;
  coordinates: AtomCoordinate[];
}

export interface AtomCoordinate {
  element: string;
  x: number;
  y: number;
  z: number;
  tag?: string;
}

export interface BasisBlock {
  basisSet: string;
  library: boolean;
  elements: string[];
}

export interface SCFBlock {
  maxiter?: number;
  thresh?: number;
  tol2e?: number;
  direct?: boolean;
  vectors?: string;
}

export interface TaskDirective {
  theory: string;
  operation: string;
}

export class NWChemParser {
  private static readonly SECTION_KEYWORDS = new Set([
    'geometry', 'basis', 'scf', 'dft', 'mp2', 'ccsd', 'ccsd(t)',
    'ecp', 'so', 'tce', 'mcscf', 'selci', 'hessian', 'vib', 'property',
    'rt_tddft', 'pspw', 'band', 'paw', 'ofpw', 'bq', 'charge', 'cons',
  ]);

  private static readonly TOP_LEVEL_KEYWORDS = new Set([
    'start', 'restart', 'title', 'echo', 'set', 'unset', 'stop',
    'task', 'charge', 'memory', 'permanent_dir', 'scratch_dir', 'print',
  ]);

  private readonly lines: string[];
  private readonly sections: Map<string, NWChemSection[]> = new Map();

  constructor(public readonly source: string) {
    this.lines = source.split(/\r?\n/);
    this.parseSections();
  }

  private parseSections(): void {
    let currentSection: NWChemSection | null = null;
    let sectionKeywords: string[] = [];
    let sectionContent: string[] = [];

    for (let i = 0; i < this.lines.length; i++) {
      const line = this.lines[i];
      const stripped = line.trim().toLowerCase();

      if (!stripped || stripped.startsWith('#')) {
        if (currentSection) {
          sectionContent.push(line);
        }
        continue;
      }

      const parts = stripped.split(/\s+/);
      const keyword = parts[0];

      if (NWChemParser.SECTION_KEYWORDS.has(keyword)) {
        // Close previous section if exists
        if (currentSection) {
          currentSection.endLine = i - 1;
          currentSection.content = [...sectionContent];
          currentSection.keywords = [...sectionKeywords];
          this.addSection(currentSection);
        }

        // Start new section
        const sectionName = keyword;
        sectionKeywords = [];
        sectionContent = [line];
        currentSection = {
          name: sectionName,
          startLine: i,
          endLine: null,
          keywords: [],
          content: [],
        };
      } else if (stripped === 'end' && currentSection) {
        sectionContent.push(line);
        currentSection.endLine = i;
        currentSection.content = [...sectionContent];
        currentSection.keywords = [...sectionKeywords];
        this.addSection(currentSection);
        currentSection = null;
        sectionKeywords = [];
        sectionContent = [];
      } else {
        if (currentSection) {
          sectionContent.push(line);
          if (parts.length > 0) {
            const firstWord = parts[0];
            if (!firstWord.startsWith('#')) {
              sectionKeywords.push(firstWord);
            }
          }
        }
      }
    }

    // Handle unclosed section
    if (currentSection) {
      currentSection.endLine = this.lines.length - 1;
      currentSection.content = [...sectionContent];
      currentSection.keywords = [...sectionKeywords];
      this.addSection(currentSection);
    }
  }

  private addSection(section: NWChemSection): void {
    const existing = this.sections.get(section.name) || [];
    existing.push(section);
    this.sections.set(section.name, existing);
  }

  getSectionAtLine(lineNumber: number): string | null {
    for (const [, sections] of this.sections) {
      for (const section of sections) {
        if (section.startLine <= lineNumber && 
            (section.endLine === null || lineNumber <= section.endLine)) {
          return section.name;
        }
      }
    }
    return null;
  }

  getContext(lineNumber: number, column: number): ParseContext {
    if (lineNumber < 0 || lineNumber >= this.lines.length) {
      return {
        lineNumber,
        column,
        currentSection: null,
        sectionStack: [],
        lineContent: '',
        wordAtCursor: '',
        isInBlock: false,
      };
    }

    const lineContent = this.lines[lineNumber];
    const currentSection = this.getSectionAtLine(lineNumber);
    const sectionStack: string[] = currentSection ? [currentSection] : [];
    const wordAtCursor = this.getWordAtPosition(lineContent, column);
    const isInBlock = currentSection !== null;

    return {
      lineNumber,
      column,
      currentSection,
      sectionStack,
      lineContent,
      wordAtCursor,
      isInBlock,
    };
  }

  private getWordAtPosition(line: string, column: number): string {
    if (!line || column < 0 || column > line.length) {
      return '';
    }

    let start = column;
    let end = column;

    while (start > 0 && /[a-zA-Z0-9_]/.test(line[start - 1])) {
      start--;
    }

    while (end < line.length && /[a-zA-Z0-9_]/.test(line[end])) {
      end++;
    }

    return line.substring(start, end);
  }

  getCompletionContext(lineNumber: number, column: number): {
    type: string;
    section: string | null;
    word: string;
    line: string;
    inBlock: boolean;
  } {
    const context = this.getContext(lineNumber, column);
    const lineContent = context.lineContent.trim().toLowerCase();

    let completionType = 'top_level';

    if (context.currentSection) {
      completionType = context.currentSection;
    } else if (lineContent.startsWith('task')) {
      completionType = 'task_operation';
    } else if (lineContent.startsWith('basis') || lineContent.includes('library')) {
      completionType = 'basis_set';
    } else if (lineContent.startsWith('dft') || lineContent.startsWith('xc')) {
      completionType = 'dft_functional';
    }

    return {
      type: completionType,
      section: context.currentSection,
      word: context.wordAtCursor,
      line: lineContent,
      inBlock: context.isInBlock,
    };
  }

  getAllSections(): string[] {
    return Array.from(this.sections.keys());
  }

  getSectionContent(sectionName: string): NWChemSection[] {
    return this.sections.get(sectionName.toLowerCase()) || [];
  }

  isValidSyntax(): { valid: boolean; errors: Array<{ line: number; message: string }> } {
    const errors: Array<{ line: number; message: string }> = [];
    const openSections: Array<{ name: string; startLine: number }> = [];

    for (let i = 0; i < this.lines.length; i++) {
      const stripped = this.lines[i].trim().toLowerCase();

      if (!stripped || stripped.startsWith('#')) {
        continue;
      }

      const parts = stripped.split(/\s+/);
      if (parts.length === 0) {
        continue;
      }

      const keyword = parts[0];

      if (NWChemParser.SECTION_KEYWORDS.has(keyword)) {
        openSections.push({ name: keyword, startLine: i });
      } else if (keyword === 'end') {
        if (openSections.length === 0) {
          errors.push({
            line: i,
            message: "Unexpected 'end' keyword (no matching section start)",
          });
        } else {
          openSections.pop();
        }
      }
    }

    for (const section of openSections) {
      errors.push({
        line: section.startLine,
        message: `Unclosed section: '${section.name}'`,
      });
    }

    return { valid: errors.length === 0, errors };
  }

  // ===== Specific Block Parsers =====

  parseGeometryBlock(): GeometryBlock | null {
    const sections = this.sections.get('geometry');
    if (!sections || sections.length === 0) {
      return null;
    }

    const section = sections[0];
    const atoms: AtomCoordinate[] = [];
    let units = 'angstroms'; // default

    for (const line of section.content) {
      const trimmed = line.trim();
      
      // Skip comments and empty lines
      if (!trimmed || trimmed.startsWith('#')) {
        continue;
      }

      // Check for units specification
      const lowerLine = trimmed.toLowerCase();
      if (lowerLine.includes('units')) {
        const match = lowerLine.match(/units\s+(\w+)/);
        if (match) {
          units = match[1];
        }
        continue;
      }

      // Skip end keyword
      if (lowerLine === 'end' || lowerLine.startsWith('end ')) {
        continue;
      }

      // Parse atom coordinates: "C 0.0 0.0 0.0" or "C 0.0 0.0 0.0 tag"
      const parts = trimmed.split(/\s+/);
      if (parts.length >= 4) {
        const element = parts[0];
        const x = parseFloat(parts[1]);
        const y = parseFloat(parts[2]);
        const z = parseFloat(parts[3]);
        
        if (!isNaN(x) && !isNaN(y) && !isNaN(z)) {
          atoms.push({
            element,
            x,
            y,
            z,
            tag: parts.length > 4 ? parts[4] : undefined,
          });
        }
      }
    }

    return { units, coordinates: atoms };
  }

  parseBasisBlock(): BasisBlock[] {
    const sections = this.sections.get('basis');
    if (!sections) {
      return [];
    }

    return sections.map(section => {
      const elements: string[] = [];
      let basisSet = '';
      let library = false;

      for (const line of section.content) {
        const trimmed = line.trim();
        
        if (!trimmed || trimmed.startsWith('#')) {
          continue;
        }

        const lowerLine = trimmed.toLowerCase();
        if (lowerLine === 'end' || lowerLine.startsWith('end ')) {
          continue;
        }

        // Check for library keyword
        if (lowerLine.includes('library')) {
          library = true;
          const match = lowerLine.match(/library\s+(\S+)/);
          if (match) {
            basisSet = match[1];
          }
        }

        // Parse element specifications
        const parts = trimmed.split(/\s+/);
        if (parts.length >= 1 && parts[0].match(/^[A-Za-z]{1,2}$/)) {
          elements.push(parts[0]);
        }
      }

      return { basisSet, library, elements };
    });
  }

  parseSCFBlock(): SCFBlock | null {
    const sections = this.sections.get('scf');
    if (!sections || sections.length === 0) {
      return null;
    }

    const section = sections[0];
    const scf: SCFBlock = {};

    for (const line of section.content) {
      const trimmed = line.trim().toLowerCase();
      
      if (!trimmed || trimmed.startsWith('#') || trimmed === 'end') {
        continue;
      }

      // Parse maxiter
      if (trimmed.startsWith('maxiter')) {
        const match = trimmed.match(/maxiter\s+(\d+)/);
        if (match) {
          scf.maxiter = parseInt(match[1], 10);
        }
      }

      // Parse thresh
      if (trimmed.startsWith('thresh')) {
        const match = trimmed.match(/thresh\s+([\d.eE+-]+)/);
        if (match) {
          scf.thresh = parseFloat(match[1]);
        }
      }

      // Parse tol2e
      if (trimmed.startsWith('tol2e')) {
        const match = trimmed.match(/tol2e\s+([\d.eE+-]+)/);
        if (match) {
          scf.tol2e = parseFloat(match[1]);
        }
      }

      // Parse direct
      if (trimmed.startsWith('direct')) {
        scf.direct = true;
      }

      // Parse vectors
      if (trimmed.startsWith('vectors')) {
        const match = trimmed.match(/vectors\s+(.+)/);
        if (match) {
          scf.vectors = match[1].trim();
        }
      }
    }

    return scf;
  }

  parseTaskDirectives(): TaskDirective[] {
    const tasks: TaskDirective[] = [];

    for (const line of this.lines) {
      const trimmed = line.trim().toLowerCase();
      
      if (!trimmed || trimmed.startsWith('#')) {
        continue;
      }

      if (trimmed.startsWith('task')) {
        const parts = trimmed.split(/\s+/);
        if (parts.length >= 2) {
          tasks.push({
            theory: parts[1],
            operation: parts[2] || 'energy',
          });
        }
      }
    }

    return tasks;
  }
}

// Convenience function
export function parseNWChemSource(source: string): NWChemParser {
  return new NWChemParser(source);
}

export function getLineKeywords(line: string): string[] {
  const stripped = line.trim().toLowerCase();
  if (!stripped || stripped.startsWith('#')) {
    return [];
  }

  return stripped.split(/\s+/);
}
