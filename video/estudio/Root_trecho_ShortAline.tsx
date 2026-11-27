          durationMs: 35200,
          panels: [],
          endCard: null,
        }}
      />
      <Composition
        id="ShortAline"
        component={ShortAline}
        calculateMetadata={calculateShortAlineMetadata}
        width={1080}
        height={1920}
        defaultProps={alineDefaults}
      />
      <Composition
        id="ShortAline45"
        component={ShortAline}
        calculateMetadata={calculateShortAlineMetadata}
        width={1080}
        height={1350}
        defaultProps={alineDefaults}
      />
      <Composition
        id="Wide"
        component={Short}
        calculateMetadata={calculateShortMetadata}
        width={1920}
