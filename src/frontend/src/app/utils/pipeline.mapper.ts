import { AlgorithmUI, ParameterUI } from '../models/ui/forms.ui';
import { AlgorithmStep, DomainType } from '../models/api/preprocessing.model.api';
import { ValidatorsUtil } from './validators';

export class PipelineMapper {

  /**
   * Converts the UI List (Algorithms with checkboxes/errors) 
   * into the Strict API Payload (Name + Params).
   */
  static toApiPipeline(algorithms: AlgorithmUI[], selectedDomain: DomainType): AlgorithmStep[] {
    return algorithms
      .filter((a) => this.isAlgorithmEnabledAndInDomain(a, selectedDomain))
      .map((a) => ({
        name: a.id, // Ensure this matches backend registry name
        params: this.mapParams(a.params),
      }));
  }

  /**
   * Creates the summary config object for the Results Page logic
   */
  static toResultsConfig(algorithms: AlgorithmUI[], selectedDomain: DomainType): any[] {
    return algorithms
      .filter((a) => this.isAlgorithmEnabledAndInDomain(a, selectedDomain))
      .map((a) => ({
        name: a.id,
        displayName: a.name,
        params: this.mapParams(a.params),
      }));
  }

  private static isAlgorithmEnabledAndInDomain(a: AlgorithmUI, domain: DomainType): boolean {
    if (!a.enabled) return false;
    if (!a.domainType) return true;
    return a.domainType === domain;
  }

  private static mapParams(params: ParameterUI[]): Record<string, any> {
    const out: Record<string, any> = {};

    params.forEach((p) => {
      let value = p.value;
      if (ValidatorsUtil.isNumericType(p.type)) {
        value = Number(p.value);
      }
      out[p.name] = value;
    });

    return out;
  }
}