import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';

// Services & Models
import { AlgorithmService } from '../../services/algorithm.service';
import {
  AlgorithmInfo,
  AlgorithmType,
} from '../../models/api/algorithm-library.model.api';

import { AlgorithmDetailsComponent } from '../algorithm-details/algorithm-details.component';
import { AppLoaderComponent } from '../ui/app-loader/app-loader.component';

@Component({
  selector: 'app-algorithm-library',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    AlgorithmDetailsComponent,
    AppLoaderComponent,
  ],
  templateUrl: './algorithm-library.component.html',
  styleUrls: [],
})
export class AlgorithmLibraryComponent implements OnInit {
  // Data
  algorithms: AlgorithmInfo[] = [];
  isLoading = false;
  error = '';

  // Search & Filter State
  searchQuery = '';
  selectedType: AlgorithmType | null = null;
  selectedCategory: string | null = null;

  // Options for Filters
  algorithmTypes = [
    { label: 'Preprocessing', value: 'preprocessing' },
    { label: 'Analysis', value: 'analysis' },
  ];

  categories: string[] = [];

  selectedAlgorithmId: string | null = null;
  selectedAlgorithmType: 'preprocessing' | 'analysis' = 'preprocessing';
  showDetailsPanel = false;

  constructor(private algorithmService: AlgorithmService) {}

  ngOnInit(): void {
    this.loadAlgorithms();
  }

  loadAlgorithms(): void {
    this.isLoading = true;
    this.error = '';

    this.algorithmService.getAllAlgorithms().subscribe({
      next: (data) => {
        this.algorithms = data;
        // Extract unique categories for the filter buttons
        this.categories = [...new Set(data.map((a) => a.category))].sort();
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Failed to load algorithms', err);
        this.error =
          'Failed to load algorithm library. Please check server connection.';
        this.isLoading = false;
      },
    });
  }

  // --- Filtering Logic ---

  selectType(type: string): void {
    this.selectedType = type === 'All' ? null : (type as AlgorithmType);
  }

  selectCategory(category: string | null): void {
    this.selectedCategory = category;
  }

  get filteredAlgorithms(): AlgorithmInfo[] {
    return this.algorithms.filter((algo) => {
      const matchesSearch =
        algo.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        algo.description.toLowerCase().includes(this.searchQuery.toLowerCase());

      const matchesType = this.selectedType
        ? algo.type === this.selectedType
        : true;
      const matchesCategory = this.selectedCategory
        ? algo.category === this.selectedCategory
        : true;

      return matchesSearch && matchesType && matchesCategory;
    });
  }

  // --- UI Helpers ---

  getAlgorithmTypeBadge(type: string): string {
    return type === 'preprocessing' ? 'Preprocessing' : 'Analysis';
  }

  openDetails(algorithm: AlgorithmInfo): void {
    this.selectedAlgorithmId = algorithm.id;
    this.selectedAlgorithmType = algorithm.type;
    this.showDetailsPanel = true;
  }

  closeDetails(): void {
    this.showDetailsPanel = false;
    setTimeout(() => {
      this.selectedAlgorithmId = null;
    }, 300);
  }
}
