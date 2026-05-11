import { Routes } from '@angular/router';
import { FileUploadComponent } from './components/file-upload/file-upload.component';
import { FileConfigComponent } from './components/file-config/file-config.component';
import { PreprocessingConfigComponent } from './components/preprocessing-config/preprocessing-config.component';
import { PreprocessingResultsComponent } from './components/preprocessing-results/preprocessing-results.component';
import { AnalysisDashboardComponent } from './components/analysis-dashboard/analysis-dashboard.component';
import { VisualizationComponent } from './components/visualisation/visualisation.component';
import { AlgorithmLibraryComponent } from './components/algorithm-library/algorithm-library.component';
import { AlgorithmDetailsComponent } from './components/algorithm-details/algorithm-details.component';
import { SettingsComponent } from './components/settings/settings.component';
import { AiModelsComponent } from './components/ai-models/ai-models.component';

export const routes: Routes = [
  { path: '', redirectTo: '/upload', pathMatch: 'full' },
  { path: 'upload', component: FileUploadComponent },
  { path: 'config', component: FileConfigComponent },
  { path: 'preprocess', component: PreprocessingConfigComponent },
  { path: 'results', component: PreprocessingResultsComponent },
  { path: 'analysis', component: AnalysisDashboardComponent },
  { path: 'visualization', component: VisualizationComponent },
  { path: 'ai-models', component: AiModelsComponent },
  { path: 'algorithms', component: AlgorithmLibraryComponent },
  { path: 'algorithms/:id', component: AlgorithmDetailsComponent },
  { path: 'settings', component: SettingsComponent },
  { path: '**', redirectTo: '/upload' }
];
