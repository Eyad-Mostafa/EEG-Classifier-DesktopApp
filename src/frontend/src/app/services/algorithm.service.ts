import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, forkJoin } from 'rxjs';
import { catchError, delay, map } from 'rxjs/operators';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

// 1. Import API Models
import { DomainType } from '../models/api/preprocessing.model.api';

// 2. Import UI Models
import { 
  AlgorithmInfo, 
  AlgorithmCategory 
} from '../models/api/algorithm-library.model.api';

import { AlgorithmUI } from '../models/ui/forms.ui';
import { ConfigService } from './config.service';

@Injectable({
  providedIn: 'root',
})
export class AlgorithmService {
  private preprocessingUrl: string;
  private analysisUrl: string;

  // Use AlgorithmUI instead of the missing 'Algorithm' type
  private selectedAlgorithmsSubject = new BehaviorSubject<AlgorithmUI[]>([]);
  selectedAlgorithms$ = this.selectedAlgorithmsSubject.asObservable();

  constructor(
    private http: HttpClient,
    private configService: ConfigService
  ) {
    this.preprocessingUrl = `${this.configService.getApiUrl()}/preprocess/steps`;
    this.analysisUrl = `${this.configService.getApiUrl()}/analysis/methods`;
  }

  // Fetch all algorithms from both preprocessing and analysis
  getAllAlgorithms(detailed: boolean = false): Observable<AlgorithmInfo[]> {
    return forkJoin({
      preprocessing: this.getPreprocessingAlgorithms(detailed),
      analysis: this.getAnalysisAlgorithms(detailed),
    }).pipe(
      map(({ preprocessing, analysis }) => {
        console.log('Preprocessing algorithms:', preprocessing);
        console.log('Analysis algorithms:', analysis);

        // Combine and normalize both types
        const allAlgorithms = [
          ...preprocessing.map((algo) => ({
            ...algo,
            type: 'preprocessing' as const,
          })),
          ...analysis,
        ];
        return allAlgorithms;
      }),
      catchError((error) => {
        console.error('Error fetching algorithms:', error);
        return of([] as AlgorithmInfo[]);
      })
    );
  }

  getPreprocessingAlgorithms(detailed: boolean = false): Observable<AlgorithmInfo[]> {
    const url = detailed
      ? `${this.preprocessingUrl}?detailed=true`
      : this.preprocessingUrl;

    return this.http.get<any>(url).pipe(
      map((response) => {
        let algorithms: any[] = [];

        if (Array.isArray(response)) {
          algorithms = response;
        } else if (response && typeof response === 'object') {
          algorithms = Object.values(response);
        }

        return algorithms.map((algo) => ({
          id: algo.id || algo.step_id,
          name: algo.name || algo.step_name,
          category: this.mapPreprocessingCategory(algo.category),
          domainType: this.mapDomainType(algo.domainType),
          description: algo.description || '',
          howItWorks: algo.howItWorks || '',
          parameters: algo.parameters || [],
          useCases: algo.useCases || [],
          relatedAlgorithms: algo.relatedAlgorithms || [],
          examples: algo.examples || [],
          type: 'preprocessing' as const,
        }));
      }),
      catchError((error) => {
        console.error('Error fetching preprocessing algorithms:', error);
        return of([] as AlgorithmInfo[]);
      })
    );
  }

  private mapPreprocessingCategory(category: string): AlgorithmCategory {
    const categoryMap: { [key: string]: AlgorithmCategory } = {
      'Artifact Removal': 'Artifact Removal',
      'Filtering': 'Filtering',
      'Resampling': 'Preprocessing',
      'Referencing': 'Preprocessing',
      'Time-Frequency Analysis': 'Time-Frequency',
    };
    return categoryMap[category] || 'Preprocessing';
  }

  getAnalysisAlgorithms(detailed: boolean = false): Observable<AlgorithmInfo[]> {
    const url = detailed
      ? `${this.analysisUrl}?detailed=true`
      : this.analysisUrl;
    return this.http.get<any[]>(url).pipe(
      map((analysisMethods) => {
        return analysisMethods.map((method) =>
          this.normalizeAnalysisAlgorithm(method)
        );
      }),
      catchError((error) => {
        console.error('Error fetching analysis algorithms:', error);
        return of([] as AlgorithmInfo[]);
      })
    );
  }

  private normalizeAnalysisAlgorithm(analysisMethod: any): AlgorithmInfo {
    const normalized: AlgorithmInfo = {
      id: analysisMethod.method_id || analysisMethod.id,
      name: analysisMethod.method_name || analysisMethod.name,
      category: this.mapAnalysisCategory(analysisMethod.category),
      domainType: this.mapDomainType(analysisMethod.domainType),
      description:
        analysisMethod.method_description || analysisMethod.description || '',
      howItWorks:
        analysisMethod.how_it_works || analysisMethod.howItWorks || '',
      parameters: analysisMethod.parameters || [],
      useCases: analysisMethod.use_cases || analysisMethod.useCases || [],
      relatedAlgorithms:
        analysisMethod.related_methods ||
        analysisMethod.relatedAlgorithms ||
        [],
      examples: analysisMethod.examples || [],
      type: 'analysis' as const,
    };
    return normalized;
  }

  private mapAnalysisCategory(category: string): AlgorithmCategory {
    const categoryMap: { [key: string]: AlgorithmCategory } = {
      'entropy_analysis': 'Statistical Analysis',
      'frequency_analysis': 'Frequency Analysis',
      'time_analysis': 'Statistical Analysis',
      'filtering': 'Filtering',
      'artifact_removal': 'Artifact Removal',
      'spatial': 'Preprocessing',
      'quality_analysis': 'Quality Analysis',
    };
    return categoryMap[category] || 'Statistical Analysis';
  }

  // ✅ FIX: Use Enum Values correctly (UPPERCASE from API model)
  private mapDomainType(domainType: string): DomainType {
    if (!domainType) return DomainType.TIME;

    const domainMap: { [key: string]: DomainType } = {
      'time': DomainType.TIME,
      'frequency': DomainType.FREQUENCY,
      'time_frequency': DomainType.TIME_FREQUENCY,
      'quality': DomainType.QUALITY,
    };
    return domainMap[domainType] || DomainType.TIME;
  }

  getAlgorithmById(
    id: string,
    type?: 'preprocessing' | 'analysis'
  ): Observable<AlgorithmInfo | null> {
    if (type === 'analysis') {
      return this.http.get<any>(`${this.analysisUrl}/${id}`).pipe(
        map((method) => this.normalizeAnalysisAlgorithm(method)),
        catchError((error) => {
          console.error(`Error fetching analysis algorithm ${id}:`, error);
          return of(null);
        })
      );
    } else {
      return this.http
        .get<AlgorithmInfo>(`${this.preprocessingUrl}/${id}`)
        .pipe(
          map((algo) => ({ ...algo, type: 'preprocessing' as const })),
          catchError((error) => {
            console.error(`Error fetching algorithm ${id}:`, error);
            return of(null);
          })
        );
    }
  }

  getAlgorithmsByCategory(category: AlgorithmCategory): Observable<AlgorithmInfo[]> {
    return this.getAllAlgorithms().pipe(
      map((algorithms) =>
        algorithms.filter((algo) => algo.category === category)
      )
    );
  }

  searchAlgorithms(query: string): Observable<AlgorithmInfo[]> {
    const lowerQuery = query.toLowerCase();
    return this.getAllAlgorithms().pipe(
      map((algorithms) =>
        algorithms.filter(
          (algo) =>
            algo.name.toLowerCase().includes(lowerQuery) ||
            algo.description.toLowerCase().includes(lowerQuery) ||
            algo.category.toLowerCase().includes(lowerQuery)
        )
      )
    );
  }

  setSelectedAlgorithms(algorithms: AlgorithmUI[]): void {
    this.selectedAlgorithmsSubject.next(algorithms);
  }

  getSelectedAlgorithms(): AlgorithmUI[] {
    return this.selectedAlgorithmsSubject.value;
  }

  // Validate parameters for an algorithm
  validateAlgorithmParameters(
    algorithm: AlgorithmUI
  ): Observable<{ valid: boolean; errors: string[] }> {
    const algorithmType = algorithm.type || 'preprocessing';
    return this.getAlgorithmById(algorithm.id, algorithmType).pipe(
      map((algorithmInfo) => {
        const errors: string[] = [];

        if (!algorithmInfo) {
          return { valid: false, errors: ['Algorithm not found'] };
        }

        algorithm.params.forEach((param) => {
          const paramInfo = algorithmInfo.parameters.find(
            (p) => p.name === param.name
          );
          if (!paramInfo) {
            errors.push(`Unknown parameter: ${param.name}`);
            return;
          }

          if (paramInfo.type === 'number') {
            const value = parseFloat(String(param.value));
            
            if (isNaN(value)) {
              errors.push(`${param.name} must be a number`);
            } 
            else if (paramInfo.min != null && value < paramInfo.min) {
              errors.push(`${param.name} must be >= ${paramInfo.min}`);
            } 
            else if (paramInfo.max != null && value > paramInfo.max) {
              errors.push(`${param.name} must be <= ${paramInfo.max}`);
            }
          }
        });

        return { valid: errors.length === 0, errors };
      })
    );
  }
}